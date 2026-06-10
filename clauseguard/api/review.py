from datetime import datetime, timezone
from io import BytesIO
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi.responses import StreamingResponse
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill

from clauseguard.api.deps import get_es_service, get_openai_assistant
from clauseguard.models.openai_legal import ContractReviewOutput
from clauseguard.openai_assistant import OpenAILegalAssistant
from clauseguard.services.elasticsearch_service import ElasticsearchService

router = APIRouter(prefix="/review", tags=["review"])


def _build_review_record(contract_id: str, contract_filename: str, review: ContractReviewOutput) -> dict:
    reviewed_at = datetime.now(timezone.utc).isoformat()
    payload = review.model_dump(mode="json")
    findings_count = (
        len(review.clause_analyses)
        + len(review.risk_assessments)
        + len(review.compliance_findings)
        + len(review.negotiation_strategies)
        + len(review.missing_protections)
    )
    return {
        "review_id": str(uuid4()),
        "contract_id": contract_id,
        "contract_filename": contract_filename,
        "reviewed_at": reviewed_at,
        "contract_safety_score": review.contract_safety_score,
        "summary": review.summary,
        "findings_count": findings_count,
        "review": payload,
    }


def _source_map_for_clauses(clauses: list[dict]) -> str:
    lines: list[str] = []
    for clause in clauses:
        excerpt = (clause.get("text", "") or "").strip()
        if len(excerpt) > 400:
            excerpt = excerpt[:400] + "..."
        lines.append(
            " | ".join(
                [
                    f"clause_id={clause.get('clause_id', '')}",
                    f"page={clause.get('page_number', '')}",
                    f"section={clause.get('section_number', '')}",
                    f"type={clause.get('clause_type', '')}",
                    f"offsets={clause.get('char_offset_start', '')}-{clause.get('char_offset_end', '')}",
                    f"excerpt={excerpt}",
                ]
            )
        )
    return "\n".join(lines)


def _review_from_record(record: dict) -> ContractReviewOutput:
    return ContractReviewOutput.model_validate(record.get("review") or {})


def _severity_rank(value: str) -> int:
    return {"critical": 4, "high": 3, "medium": 2, "low": 1, "info": 0}.get(str(value).lower(), 0)


def _citation_text(page: int | None, section: str, clause_id: str) -> str:
    parts = [
        f"p. {page}" if page else "",
        f"sec. {section}" if section else "",
        f"clause {clause_id}" if clause_id else "",
    ]
    return " · ".join(part for part in parts if part)


def _export_rows(review: ContractReviewOutput) -> list[tuple[str, str, str, str, str, str]]:
    rows: list[tuple[str, str, str, str, str, str]] = []

    for item in review.compliance_findings:
        rows.append(
            (
                _citation_text(item.source_page, item.source_section, item.source_clause_id) or item.requirement,
                item.explanation,
                item.severity.value,
                item.requirement,
                item.remediation,
                item.remediation,
            )
        )

    for item in review.missing_protections:
        rows.append(
            (
                _citation_text(item.source_page, item.source_section, item.source_clause_id) or item.protection,
                item.why_missing,
                "high",
                item.protection,
                item.mitigation,
                item.suggested_clause,
            )
        )

    for item in review.risk_assessments:
        rows.append(
            (
                _citation_text(item.source_page, item.source_section, item.source_clause_id) or item.risk_area,
                item.issue,
                item.severity.value,
                item.risk_area,
                item.mitigation,
                item.mitigation,
            )
        )

    for item in review.clause_analyses:
        rows.append(
            (
                _citation_text(item.source_page, item.source_section, item.source_clause_id) or item.clause_name,
                item.summary,
                item.risk_level.value if hasattr(item.risk_level, "value") else str(item.risk_level),
                item.clause_type,
                item.impact,
                "; ".join(item.recommendations) if item.recommendations else item.impact,
            )
        )

    for item in review.negotiation_strategies:
        rows.append(
            (
                _citation_text(item.source_page, item.source_section, item.source_clause_id) or item.objective,
                item.rationale,
                item.priority.value if hasattr(item.priority, "value") else str(item.priority),
                item.objective,
                item.proposed_language,
                item.proposed_language,
            )
        )

    return rows


def _build_workbook(review: ContractReviewOutput, contract_filename: str, reviewed_at: str) -> BytesIO:
    wb = Workbook()
    ws = wb.active
    ws.title = "Compliance Report"

    title_fill = PatternFill("solid", fgColor="0F243E")
    header_fill = PatternFill("solid", fgColor="2F5D8A")
    light_fill = PatternFill("solid", fgColor="F3F6FA")
    green_fill = PatternFill("solid", fgColor="D9EAD3")
    yellow_fill = PatternFill("solid", fgColor="FFF2CC")
    red_fill = PatternFill("solid", fgColor="F4CCCC")

    ws.merge_cells("A1:F1")
    ws["A1"] = "ENTERPRISE COMPLIANCE RISK ASSESSMENT REPORT"
    ws["A1"].font = Font(color="FFFFFF", bold=True, size=16)
    ws["A1"].fill = title_fill
    ws["A1"].alignment = Alignment(horizontal="center", vertical="center")

    ws["A3"] = "Contract Filename"
    ws["B3"] = contract_filename
    ws["D3"] = "Compliance Score"
    ws["E3"] = f"{review.contract_safety_score:.1f}%"
    ws["A4"] = "Audit Timestamp"
    ws["B4"] = reviewed_at
    ws["D4"] = "Risk Score"
    ws["E4"] = f"{100 - review.contract_safety_score:.1f}%"

    for cell in ("A3", "A4", "D3", "D4"):
        ws[cell].font = Font(bold=True)
    ws["E3"].font = Font(bold=True, color="1F4E79")
    ws["E4"].font = Font(bold=True, color="C00000")

    ws["A6"] = "Detailed Compliance Findings Table"
    ws["A6"].font = Font(bold=True, size=14)

    headers = [
        "Clause / Section",
        "Risk Identified",
        "Risk Level",
        "Regulation",
        "Control",
        "Recommended Redline / Mitigation",
    ]
    header_row = 8
    for col, header in enumerate(headers, start=1):
        cell = ws.cell(row=header_row, column=col, value=header)
        cell.fill = header_fill
        cell.font = Font(color="FFFFFF", bold=True)
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    for row_idx, row in enumerate(_export_rows(review), start=header_row + 1):
        for col_idx, value in enumerate(row, start=1):
            cell = ws.cell(row=row_idx, column=col_idx, value=value)
            cell.alignment = Alignment(vertical="top", wrap_text=True)
            if col_idx == 3:
                if _severity_rank(value) >= 3:
                    cell.fill = red_fill
                elif _severity_rank(value) == 2:
                    cell.fill = yellow_fill
                else:
                    cell.fill = green_fill
            elif row_idx % 2 == 0:
                cell.fill = light_fill

    widths = [28, 52, 14, 18, 22, 52]
    for idx, width in enumerate(widths, start=1):
        ws.column_dimensions[chr(64 + idx)].width = width

    ws.freeze_panes = "A9"
    ws.sheet_view.showGridLines = False

    buffer = BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer


@router.post("/{contract_id}", response_model=ContractReviewOutput)
async def review_contract(
    contract_id: str,
    assistant: OpenAILegalAssistant = Depends(get_openai_assistant),
    es: ElasticsearchService = Depends(get_es_service),
):
    """Run AI contract review on a stored contract and return the structured review."""
    contract = await es.get_contract(contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="Contract not found")

    clauses = await es.get_clauses_by_contract(contract_id)
    if not clauses:
        raise HTTPException(status_code=404, detail="No clauses found for contract")

    ordered_clauses = sorted(
        clauses,
        key=lambda clause: (
            clause.get("page_number", 1),
            clause.get("char_offset_start", 0),
            clause.get("clause_type", ""),
        ),
    )
    contract_text = "\n\n".join(
        f"[{clause.get('clause_type', 'other')}] {clause.get('text', '').strip()}".strip()
        for clause in ordered_clauses
        if clause.get("text", "").strip()
    )

    if not contract_text.strip():
        raise HTTPException(status_code=422, detail="Stored contract text is empty")

    review = await assistant.analyze_contract_text(
        contract_text,
        filename=contract.get("filename", contract_id),
        source_context=_source_map_for_clauses(ordered_clauses),
    )
    review_record = _build_review_record(contract_id, contract.get("filename", contract_id), review)
    await es.save_review(review_record)
    await es.update_contract_review_summary(contract_id, review_record)
    return review


@router.get("/{contract_id}/latest", response_model=ContractReviewOutput)
async def latest_review(
    contract_id: str,
    es: ElasticsearchService = Depends(get_es_service),
):
    record = await es.get_latest_review(contract_id)
    if not record:
        raise HTTPException(status_code=404, detail="Review not found")
    return _review_from_record(record)


@router.get("/{contract_id}/history")
async def review_history(
    contract_id: str,
    es: ElasticsearchService = Depends(get_es_service),
):
    reviews = await es.list_reviews_by_contract(contract_id)
    return [
        {
            "review_id": review.get("review_id"),
            "reviewed_at": review.get("reviewed_at"),
            "contract_filename": review.get("contract_filename", contract_id),
            "contract_safety_score": review.get("contract_safety_score", 0),
            "summary": review.get("summary", ""),
            "findings_count": review.get("findings_count", 0),
        }
        for review in reviews
    ]


@router.get("/{contract_id}/export.xlsx")
async def export_review_xlsx(
    contract_id: str,
    es: ElasticsearchService = Depends(get_es_service),
):
    record = await es.get_latest_review(contract_id)
    if not record:
        raise HTTPException(status_code=404, detail="Review not found")

    review = _review_from_record(record)
    reviewed_at = record.get("reviewed_at", "")
    contract_filename = record.get("contract_filename", contract_id)
    buffer = _build_workbook(review, contract_filename, reviewed_at)
    filename = f"{contract_filename.rsplit('.', 1)[0]}_compliance_review.xlsx"
    return Response(
        content=buffer.getvalue(),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{contract_id}/{review_id}", response_model=ContractReviewOutput)
async def get_review_by_id(
    contract_id: str,
    review_id: str,
    es: ElasticsearchService = Depends(get_es_service),
):
    record = await es.get_review_by_id(review_id)
    if not record or record.get("contract_id") != contract_id:
        raise HTTPException(status_code=404, detail="Review not found")
    return _review_from_record(record)


@router.delete("/{contract_id}")
async def delete_contract_bundle(
    contract_id: str,
    es: ElasticsearchService = Depends(get_es_service),
):
    await es.delete_reviews_by_contract(contract_id)
    await es.delete_clauses_by_contract(contract_id)
    await es.delete_contract(contract_id)
    return {"status": "deleted", "contract_id": contract_id}
