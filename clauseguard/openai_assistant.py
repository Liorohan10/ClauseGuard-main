from __future__ import annotations

import asyncio
import base64
import json
import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import fitz
from openai import AsyncOpenAI

from clauseguard.config import settings
from clauseguard.models.openai_legal import (
    AgentPromptSpec,
    ClauseAnalysisResponse,
    ComplianceAuditResponse,
    ContractReviewOutput,
    MissingProtectionResponse,
    NDAGenerationOutput,
    NegotiationStrategyResponse,
    RiskAssessmentResponse,
    SafetyScoreResponse,
    schema_instructions,
)

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class DocumentPayload:
    filename: str
    file_type: str
    text: str
    page_count: int = 1
    content: list[dict[str, Any]] | str | None = None
    source_context: str = ""


class OpenAILegalAssistant:
    """Async legal assistant powered by the OpenAI Chat Completions API."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        vision_model: str | None = None,
    ) -> None:
        self.client = AsyncOpenAI(
            api_key=api_key or settings.openai_api_key,
            base_url=base_url or settings.openai_base_url,
        )
        self.model = model or settings.openai_model
        self.vision_model = vision_model or settings.openai_vision_model

    async def analyze_contract(self, file_path: str) -> ContractReviewOutput:
        document = await self._load_document(file_path)
        return await self._analyze_document(document)

    async def analyze_contract_text(
        self,
        contract_text: str,
        filename: str = "",
        source_context: str = "",
    ) -> ContractReviewOutput:
        document = DocumentPayload(
            filename=filename or "contract.txt",
            file_type="text",
            text=contract_text,
            content=contract_text,
            source_context=source_context,
        )
        return await self._analyze_document(document)

    async def _analyze_document(self, document: DocumentPayload) -> ContractReviewOutput:
        tasks = await asyncio.gather(
            self._run_agent(
                document=document,
                spec=AgentPromptSpec(
                    role="Clause Analysis Agent",
                    instructions=(
                        "Extract the most important clauses in the contract. "
                        "Return 5-12 significant items with clause text, normalized clause type, "
                        "summary, risk level, impact, recommendations, and exact citation fields. "
                        "For each item, include source_page, source_section, source_clause_id, and source_excerpt. "
                        "Prioritize indemnity, liability, termination, confidentiality, privacy, "
                        "ownership, payment, and dispute resolution provisions."
                    ),
                ),
                schema=ClauseAnalysisResponse,
            ),
            self._run_agent(
                document=document,
                spec=AgentPromptSpec(
                    role="Risk Assessment Agent",
                    instructions=(
                        "Identify the main legal, commercial, operational, and enforcement risks. "
                        "Return concrete risk items with severity, issue, rationale, mitigation, citation fields, and confidence. "
                        "For each item, include source_page, source_section, source_clause_id, and source_excerpt."
                    ),
                ),
                schema=RiskAssessmentResponse,
            ),
            self._run_agent(
                document=document,
                spec=AgentPromptSpec(
                    role="Compliance Audit Agent",
                    instructions=(
                        "Audit the contract for common compliance obligations and enterprise controls, "
                        "including privacy, confidentiality, data security, retention, audit rights, and legal compliance. "
                        "Return findings with status, severity, explanation, evidence, remediation, citation fields, and confidence. "
                        "For each finding, include source_page, source_section, source_clause_id, and source_excerpt."
                    ),
                ),
                schema=ComplianceAuditResponse,
            ),
            self._run_agent(
                document=document,
                spec=AgentPromptSpec(
                    role="Negotiation Strategy Agent",
                    instructions=(
                        "Propose negotiation strategies that a buyer, vendor, or customer could use to improve the deal. "
                        "Return concise objective, leverage, proposed_language, rationale, priority, citation fields, and confidence. "
                        "For each item, include source_page, source_section, source_clause_id, and source_excerpt."
                    ),
                ),
                schema=NegotiationStrategyResponse,
            ),
            self._run_agent(
                document=document,
                spec=AgentPromptSpec(
                    role="Missing Protections Agent",
                    instructions=(
                        "Identify missing, weak, or one-sided protections that should be added to the contract. "
                        "Return each protection gap with why_missing, risk, mitigation, suggested_clause, citation fields, and confidence. "
                        "For each item, include source_page, source_section, source_clause_id, and source_excerpt."
                    ),
                ),
                schema=MissingProtectionResponse,
            ),
            return_exceptions=True,
        )

        clause_result = self._unwrap_response(tasks[0], ClauseAnalysisResponse)
        risk_result = self._unwrap_response(tasks[1], RiskAssessmentResponse)
        compliance_result = self._unwrap_response(tasks[2], ComplianceAuditResponse)
        negotiation_result = self._unwrap_response(tasks[3], NegotiationStrategyResponse)
        missing_result = self._unwrap_response(tasks[4], MissingProtectionResponse)

        safety_score = self._derive_safety_score(
            clause_result,
            risk_result,
            compliance_result,
            missing_result,
        )
        summary = self._derive_summary(
            document=document,
            clause_result=clause_result,
            risk_result=risk_result,
            compliance_result=compliance_result,
            missing_result=missing_result,
            safety_score=safety_score,
        )

        return ContractReviewOutput(
            contract_safety_score=safety_score,
            summary=summary,
            clause_analyses=clause_result.items,
            risk_assessments=risk_result.items,
            compliance_findings=compliance_result.items,
            negotiation_strategies=negotiation_result.items,
            missing_protections=missing_result.items,
            source_filename=document.filename,
            document_type=document.file_type,
        )

    async def assess_risks(self, file_path: str) -> RiskAssessmentResponse:
        document = await self._load_document(file_path)
        return await self._run_agent(
            document=document,
            spec=AgentPromptSpec(
                role="Risk Assessment Agent",
                instructions=(
                    "Identify the main legal, commercial, operational, and enforcement risks. "
                    "Return concrete risk items with severity, issue, rationale, mitigation, and confidence."
                ),
            ),
            schema=RiskAssessmentResponse,
        )

    async def generate_nda(self, description: str) -> NDAGenerationOutput:
        system_message = (
            "You are a legal drafting assistant. Draft a practical, business-friendly NDA from the user's description. "
            "Return only JSON that matches the schema exactly. "
            f"{schema_instructions(NDAGenerationOutput)}"
        )
        response = await self._chat_json(
            model=self.model,
            system_message=system_message,
            user_content=description,
        )
        return self._parse_model(response, NDAGenerationOutput)

    async def _run_agent(
        self,
        document: DocumentPayload,
        spec: AgentPromptSpec,
        schema: type,
    ):
        system_message = (
            f"You are {spec.role}. {spec.instructions} "
            f"{schema_instructions(schema)}"
        )
        user_content = document.content if document.content is not None else document.text
        if document.source_context:
            user_content = (
                f"CONTRACT TEXT:\n{user_content}\n\n"
                f"SOURCE MAP:\n{document.source_context}\n\n"
                "Use the SOURCE MAP to cite the exact page, section, clause id, and excerpt for each finding."
            )
        response = await self._chat_json(
            model=self.vision_model if self._use_vision(document) else self.model,
            system_message=system_message,
            user_content=user_content,
        )
        return self._parse_model(response, schema)

    async def _chat_json(
        self,
        model: str,
        system_message: str,
        user_content: str | list[dict[str, Any]],
    ) -> str:
        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_content},
        ]
        try:
            logger.info("OpenAI request: model=%s, sys_len=%d, user_len=%d", model, len(system_message), len(str(user_content)))
            response = await self.client.chat.completions.create(
                model=model,
                messages=messages,
                response_format={"type": "json_object"},
                temperature=0.2,
            )
            resp_id = getattr(response, "id", None) or (response.to_dict().get("id") if hasattr(response, "to_dict") else None)
            logger.info("OpenAI response received: id=%s", resp_id)
            # Dump raw response for inspection when configured
            try:
                dump_dir = Path(settings.openai_dump_dir or "openai_dumps")
                dump_dir.mkdir(parents=True, exist_ok=True)
                timestamp = int(time.time())
                model_safe = model.replace("/", "_")
                fname = f"{resp_id or 'noid'}_{model_safe}_{timestamp}.json"
                fpath = dump_dir / fname
                # Attempt to get a serializable dict from response
                data = None
                if hasattr(response, "to_dict"):
                    try:
                        data = response.to_dict()
                    except Exception:
                        data = None
                if data is None:
                    try:
                        data = json.loads(str(response))
                    except Exception:
                        data = {"repr": str(response)}
                fpath.write_text(json.dumps(data, indent=2), encoding="utf-8")
                logger.info("OpenAI raw response dumped to %s", fpath)
            except Exception:
                logger.exception("Failed to dump OpenAI response to file")
            content = response.choices[0].message.content or "{}"
            return content.strip()
        except Exception:
            logger.exception("OpenAI request failed for model %s", model)
            raise

    def _parse_model(self, raw_json: str, schema: type):
        try:
            return schema.model_validate_json(raw_json)
        except Exception:
            logger.exception("Failed to parse OpenAI JSON for %s", schema.__name__)
            return schema.model_validate(self._fallback_payload(schema))

    def _unwrap_response(self, value: Any, schema: type):
        if isinstance(value, Exception):
            logger.exception("Agent execution failed", exc_info=value)
            return schema.model_validate(self._fallback_payload(schema))
        return value

    def _fallback_payload(self, schema: type) -> dict[str, Any]:
        fallback = {
            "ClauseAnalysisResponse": {"items": []},
            "RiskAssessmentResponse": {"items": []},
            "ComplianceAuditResponse": {"items": []},
            "NegotiationStrategyResponse": {"items": []},
            "MissingProtectionResponse": {"items": []},
            "NDAGenerationOutput": {
                "title": "Non-Disclosure Agreement",
                "party_a": "Party A",
                "party_b": "Party B",
                "effective_date": "Effective Date",
                "confidentiality_terms": [],
                "mutuality": "mutual",
                "governing_law": "Governing law to be specified",
                "full_text": "",
            },
            "SafetyScoreResponse": {"contract_safety_score": 0, "summary": ""},
            "ContractReviewOutput": {
                "contract_safety_score": 0,
                "summary": "",
                "clause_analyses": [],
                "risk_assessments": [],
                "compliance_findings": [],
                "negotiation_strategies": [],
                "missing_protections": [],
                "source_filename": "",
                "document_type": "contract",
            },
        }
        return fallback.get(schema.__name__, {})

    async def _load_document(self, file_path: str) -> DocumentPayload:
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(file_path)

        suffix = path.suffix.lower()
        if suffix in {".txt", ".text", ".md"}:
            text = path.read_text(encoding="utf-8", errors="replace")
            return DocumentPayload(filename=path.name, file_type="text", text=text, content=text)

        if suffix == ".pdf":
            return self._load_pdf(path)

        if suffix in {".png", ".jpg", ".jpeg", ".webp"}:
            content = self._image_content(path)
            return DocumentPayload(
                filename=path.name,
                file_type="image",
                text="",
                content=content,
            )

        text = path.read_text(encoding="utf-8", errors="replace")
        return DocumentPayload(filename=path.name, file_type="text", text=text, content=text)

    def _load_pdf(self, path: Path) -> DocumentPayload:
        doc = fitz.open(path)
        try:
            page_texts: list[str] = []
            page_images: list[dict[str, Any]] = []
            for index, page in enumerate(doc):
                text = page.get_text("text").strip()
                if text:
                    page_texts.append(f"[Page {index + 1}]\n{text}")
                elif index < 3:
                    page_images.append(self._page_image_content(page, index + 1))

            extracted_text = "\n\n".join(page_texts).strip()
            if extracted_text:
                return DocumentPayload(
                    filename=path.name,
                    file_type="pdf",
                    text=extracted_text,
                    page_count=max(doc.page_count, 1),
                    content=extracted_text,
                )

            return DocumentPayload(
                filename=path.name,
                file_type="pdf",
                text="",
                page_count=max(doc.page_count, 1),
                content=page_images,
            )
        finally:
            doc.close()

    def _page_image_content(self, page: fitz.Page, page_number: int) -> dict[str, Any]:
        pixmap = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
        image_bytes = pixmap.tobytes("png")
        encoded = base64.b64encode(image_bytes).decode("utf-8")
        return {
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{encoded}"},
        }

    def _image_content(self, path: Path) -> list[dict[str, Any]]:
        encoded = base64.b64encode(path.read_bytes()).decode("utf-8")
        mime = "image/png"
        if path.suffix.lower() in {".jpg", ".jpeg"}:
            mime = "image/jpeg"
        elif path.suffix.lower() == ".webp":
            mime = "image/webp"
        return [
            {"type": "text", "text": "Analyze this contract image and extract the key legal clauses and risks."},
            {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{encoded}"}},
        ]

    def _use_vision(self, document: DocumentPayload) -> bool:
        return document.file_type in {"image"} or (
            document.file_type == "pdf" and isinstance(document.content, list)
        )

    def _derive_safety_score(
        self,
        clause_result: ClauseAnalysisResponse,
        risk_result: RiskAssessmentResponse,
        compliance_result: ComplianceAuditResponse,
        missing_result: MissingProtectionResponse,
    ) -> int:
        score = 100
        score -= len([item for item in clause_result.items if str(item.risk_level) in {"critical", "high"}]) * 5
        score -= len([item for item in risk_result.items if str(item.severity) == "high"]) * 8
        score -= len([item for item in risk_result.items if str(item.severity) == "medium"]) * 4
        score -= len([item for item in compliance_result.items if str(item.severity) in {"high", "medium"}]) * 6
        score -= len(missing_result.items) * 5
        return max(0, min(100, score))

    def _derive_summary(
        self,
        document: DocumentPayload,
        clause_result: ClauseAnalysisResponse,
        risk_result: RiskAssessmentResponse,
        compliance_result: ComplianceAuditResponse,
        missing_result: MissingProtectionResponse,
        safety_score: int,
    ) -> str:
        signals = []
        if risk_result.items:
            signals.append(f"{len(risk_result.items)} risk findings")
        if compliance_result.items:
            signals.append(f"{len(compliance_result.items)} compliance findings")
        if missing_result.items:
            signals.append(f"{len(missing_result.items)} missing protections")
        if clause_result.items:
            signals.append(f"{len(clause_result.items)} clause analyses")

        detail = ", ".join(signals) if signals else "no material issues identified"
        return (
            f"Review of {document.filename} completed with a safety score of {safety_score}/100. "
            f"The assistant identified {detail}. "
            "Use the PDF report for clause-level detail, negotiation points, and remediation guidance."
        )
