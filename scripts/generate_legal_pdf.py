from __future__ import annotations

from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from clauseguard.models.openai_legal import ContractReviewOutput


def _as_review(review: ContractReviewOutput | dict[str, Any]) -> ContractReviewOutput:
    if isinstance(review, ContractReviewOutput):
        return review
    return ContractReviewOutput.model_validate(review)


def _paragraph(styles: dict[str, ParagraphStyle], text: str, key: str = "BodyText") -> Paragraph:
    return Paragraph(text.replace("\n", "<br/>") or "&nbsp;", styles[key])


def _section_heading(styles: dict[str, ParagraphStyle], text: str) -> Paragraph:
    return Paragraph(text, styles["Heading2"])


def _build_table(headers: list[str], rows: list[list[str]]) -> Table:
    data = [headers] + rows if rows else [headers, ["No findings", "", "", ""][: len(headers)]]
    table = Table(data, repeatRows=1, hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("LEADING", (0, 0), (-1, -1), 11),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.HexColor("#f8fafc")]),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return table


def generate_legal_pdf(
    review: ContractReviewOutput | dict[str, Any],
    output_path: str | Path | None = None,
) -> Path:
    """Render a professional legal review PDF from structured OpenAI output."""
    data = _as_review(review)
    output = Path(output_path) if output_path else Path(data.source_filename or "contract_review").with_suffix(".pdf")
    if not output.is_absolute():
        output = Path.cwd() / output

    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="TitleCentered",
            parent=styles["Title"],
            alignment=TA_CENTER,
            textColor=colors.HexColor("#0f172a"),
            fontName="Helvetica-Bold",
            fontSize=20,
            leading=24,
        )
    )
    styles.add(
        ParagraphStyle(
            name="MetricLabel",
            parent=styles["BodyText"],
            fontSize=9,
            textColor=colors.HexColor("#475569"),
            leading=11,
        )
    )
    styles.add(
        ParagraphStyle(
            name="MetricValue",
            parent=styles["Heading1"],
            fontSize=24,
            leading=28,
            textColor=colors.HexColor("#0f172a"),
        )
    )

    story: list[Any] = []
    story.append(Paragraph("AI Legal Review Report", styles["TitleCentered"]))
    story.append(Spacer(1, 0.15 * inch))

    metrics = Table(
        [
            [
                Paragraph("Safety Score", styles["MetricLabel"]),
                Paragraph(f"{data.contract_safety_score}/100", styles["MetricValue"]),
                Paragraph("Document", styles["MetricLabel"]),
                Paragraph(data.source_filename or "Unknown", styles["BodyText"]),
            ]
        ],
        colWidths=[1.2 * inch, 1.0 * inch, 1.0 * inch, 3.8 * inch],
    )
    metrics.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#eff6ff")),
                ("BOX", (0, 0), (-1, -1), 0.75, colors.HexColor("#93c5fd")),
                ("INNERGRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#bfdbfe")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
            ]
        )
    )
    story.append(metrics)
    story.append(Spacer(1, 0.2 * inch))

    story.append(_section_heading(styles, "Executive Summary"))
    story.append(Spacer(1, 0.06 * inch))
    story.append(_paragraph(styles, data.summary))
    story.append(Spacer(1, 0.18 * inch))

    story.append(_section_heading(styles, "Clause Analyses"))
    clause_rows = [
        [
            item.clause_name,
            item.clause_type,
            item.risk_level.value,
            item.summary,
        ]
        for item in data.clause_analyses
    ]
    story.append(_build_table(["Clause", "Type", "Risk", "Summary"], clause_rows))
    story.append(Spacer(1, 0.18 * inch))

    story.append(_section_heading(styles, "Risk Assessments"))
    risk_rows = [
        [item.risk_area, item.severity.value, item.issue, item.mitigation] for item in data.risk_assessments
    ]
    story.append(_build_table(["Area", "Severity", "Issue", "Mitigation"], risk_rows))
    story.append(Spacer(1, 0.18 * inch))

    story.append(_section_heading(styles, "Compliance Audit"))
    compliance_rows = [
        [item.requirement, item.status, item.severity.value, item.remediation]
        for item in data.compliance_findings
    ]
    story.append(_build_table(["Requirement", "Status", "Severity", "Remediation"], compliance_rows))
    story.append(Spacer(1, 0.18 * inch))

    story.append(_section_heading(styles, "Negotiation Strategies"))
    negotiation_rows = [
        [item.objective, item.priority.value, item.proposed_language, item.rationale]
        for item in data.negotiation_strategies
    ]
    story.append(_build_table(["Objective", "Priority", "Suggested Language", "Rationale"], negotiation_rows))
    story.append(Spacer(1, 0.18 * inch))

    story.append(_section_heading(styles, "Missing Protections"))
    missing_rows = [
        [item.protection, item.risk, item.mitigation, item.suggested_clause]
        for item in data.missing_protections
    ]
    story.append(_build_table(["Protection", "Risk", "Mitigation", "Suggested Clause"], missing_rows))

    doc = SimpleDocTemplate(
        str(output),
        pagesize=letter,
        rightMargin=0.65 * inch,
        leftMargin=0.65 * inch,
        topMargin=0.7 * inch,
        bottomMargin=0.65 * inch,
        title="AI Legal Review Report",
        author="ClauseGuard",
    )
    doc.build(story)
    return output


if __name__ == "__main__":
    raise SystemExit("Import generate_legal_pdf() from the CLI instead of running this module directly.")
