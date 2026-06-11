"""
clauseguard.openai_assistant
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Specialized Data Privacy & Export Control compliance review engine.

Agent pipeline (4 specialized agents, per pasted_content.txt specification):

  1. JurisdictionProfileAgent   — identifies all applicable privacy + export-control
                                   jurisdictions with basis and applicable laws.
  2. DataPrivacyComplianceAgent — runs 15 baseline tests + jurisdiction-specific checks
                                   against all privacy laws in Appendix A.
  3. ExportControlSanctionsAgent— fires ONLY when export triggers are detected in the
                                   contract text; performs EAR/OFAC/EU dual-use analysis.
  4. RedlineAndDecisionAgent    — proposes exact redlines + issues the final decision
                                   (PASS / CONDITIONAL PASS / FAIL / ESCALATE).

Operating guardrails injected into every agent:
  • Never provide legal advice or regulatory certification.
  • Operate conservatively; escalate ambiguous cases.
  • Distinguish mandatory law vs. guidance vs. policy.
  • Never invent facts, obligations, or transfer mechanisms.
  • Always cite exact clause/section relied upon.
  • Increase scrutiny for AI/ML services.
"""
from __future__ import annotations

import asyncio
import base64
import json
import logging
import types
import typing
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import fitz
from openai import AsyncOpenAI
from pydantic import BaseModel
from pydantic_core import PydanticUndefined

from clauseguard.config import settings
from clauseguard.legal_knowledge import (
    build_full_jurisdiction_reference,
    build_guardrails_block,
    build_jurisdiction_law_summary,
    build_jurisdiction_privacy_instructions,
    build_jurisdiction_special_rules_block,
    build_operating_rules_block,
    build_privacy_tests_block,
    BASELINE_EXPORT_TESTS,
    CRITICAL_PRIVACY_CONDITIONS,
    HIGH_PRIVACY_CONDITIONS,
    DECISION_LOGIC,
    EXPORT_CONTROL_REDLINE_MINIMUM,
    JURISDICTION_EXPORT_INSTRUCTIONS,
    PRIVACY_REDLINE_MINIMUM,
    detect_export_control_trigger,
)
from clauseguard.search import async_web_search, format_search_results
from clauseguard.models.openai_legal import (
    AgentPromptSpec,
    ClauseAnalysisResponse,
    ComplianceAuditResponse,
    ContractReviewOutput,
    FinalDecision,
    DecisionOutcome,
    JurisdictionProfile,
    JurisdictionProfileResponse,
    MissingProtectionResponse,
    NDAGenerationOutput,
    NegotiationStrategyResponse,
    RedlineResponse,
    RiskAssessmentResponse,
    schema_instructions,
)

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Shared prompt blocks (injected into every agent's system message)
# ---------------------------------------------------------------------------
_OPERATING_RULES = build_operating_rules_block()
_GUARDRAILS = build_guardrails_block()
# Full 28-jurisdiction reference: law table + structural special rules + privacy instructions
_FULL_JURISDICTION_REFERENCE = build_full_jurisdiction_reference()
# Compact law summary (used in jurisdiction identification agent for brevity)
_JURISDICTION_LAW_SUMMARY = build_jurisdiction_law_summary()
# Structural special rules for all 28 jurisdictions
_JURISDICTION_SPECIAL_RULES = build_jurisdiction_special_rules_block()
_PRIVACY_TESTS = build_privacy_tests_block()
_JURISDICTION_PRIVACY_INSTRUCTIONS = build_jurisdiction_privacy_instructions()

# Export control baseline tests formatted for prompt injection
_EXPORT_TESTS = "\n".join(
    f"{i}. {t}" for i, t in enumerate(BASELINE_EXPORT_TESTS, 1)
)
_EXPORT_JURISDICTION_INSTRUCTIONS = "\n\n".join(
    f"[{j}]\n{inst}"
    for j, inst in JURISDICTION_EXPORT_INSTRUCTIONS.items()
)
_CRITICAL_CONDITIONS = "\n".join(
    f"• {c}" for c in CRITICAL_PRIVACY_CONDITIONS
)
_HIGH_CONDITIONS = "\n".join(
    f"• {c}" for c in HIGH_PRIVACY_CONDITIONS
)
_DECISION_LOGIC = "\n".join(
    f"• {k.upper()}: {v}"
    for k, v in DECISION_LOGIC.items()
)
_PRIVACY_REDLINES = "\n".join(
    f"• {r}" for r in PRIVACY_REDLINE_MINIMUM
)
_EXPORT_REDLINES = "\n".join(
    f"• {r}" for r in EXPORT_CONTROL_REDLINE_MINIMUM
)


# ---------------------------------------------------------------------------
# Document payload
# ---------------------------------------------------------------------------

@dataclass(slots=True)
class DocumentPayload:
    filename: str
    file_type: str
    text: str
    page_count: int = 1
    content: list[dict[str, Any]] | str | None = None
    source_context: str = ""


# ---------------------------------------------------------------------------
# Agent system prompts
# ---------------------------------------------------------------------------

def _jurisdiction_agent_instructions() -> str:
    return f"""\
You are the Jurisdiction Profile Agent for ClauseGuard, an AI contract compliance review agent
specialising exclusively in Data Privacy and Export Control / Sanctions compliance.

YOUR TASK:
Identify ALL applicable privacy jurisdictions and (where triggered) export-control jurisdictions
from the contract text. For each jurisdiction, state the basis and list the applicable laws.

JURISDICTION IDENTIFICATION RULES FOR PRIVACY:
Apply a privacy jurisdiction if ANY of the following are true:
• A party is established there
• Goods/services are offered to people there
• Personal data is collected from people there
• Processing occurs there
• Data is stored there
• Data is accessed there
• Support is delivered there
• Subprocessors, affiliates, or offshore teams are located there
• Data subjects are located there

JURISDICTION IDENTIFICATION RULES FOR EXPORT CONTROL:
Apply an export-control jurisdiction ONLY if any of the following are true:
• Controlled items/software/technology originate there
• An export, reexport, transfer, transit, or remote-access event occurs there
• A sanctioned-country nexus exists
• A restricted end user/end use exists
If NONE of these conditions are met, set export_control_triggered = false.

IMPORTANT — ALL 28 JURISDICTIONS HAVE SPECIFIC RULES:
Do not simplify any jurisdiction. The reference table below contains jurisdiction-specific structural
rules, applicable laws, and procedural nuances for ALL 28 jurisdictions in our knowledge base.
Apply the rules for every jurisdiction you identify in this contract.

{_FULL_JURISDICTION_REFERENCE}

{_OPERATING_RULES}

{_GUARDRAILS}
"""


def _privacy_agent_instructions() -> str:
    return f"""\
You are the Data Privacy Compliance Agent for ClauseGuard, an AI contract compliance review agent
specialising exclusively in Data Privacy compliance.

YOUR TASK:
Review the contract for data privacy compliance across ALL identified applicable jurisdictions.
Do not limit your review to a single jurisdiction — apply the law of EVERY jurisdiction that is
relevant to this contract (identified from party establishment, data subject locations, processing
locations, data storage locations, subprocessor locations, support delivery locations, etc.).
Assign each finding an Issue ID in the format PRIV-001, PRIV-002, etc.
Set domain = "privacy" on all findings.

CRITICAL PRIVACY CONDITIONS (mark severity = "critical" if any apply):
{_CRITICAL_CONDITIONS}

HIGH PRIVACY CONDITIONS (mark severity = "high" if any apply):
{_HIGH_CONDITIONS}

{_PRIVACY_TESTS}

AI/ML HEIGHTENED SCRUTINY:
If the contract involves AI/ML services, datasets, training data, model weights, telemetry,
or employee monitoring, increase privacy scrutiny by one level and assess whether data-use
clauses allow impermissible secondary use.

COMPREHENSIVE JURISDICTION REFERENCE (all 28 jurisdictions — apply for every jurisdiction identified):
{_FULL_JURISDICTION_REFERENCE}

{_OPERATING_RULES}

{_GUARDRAILS}

OUTPUT REQUIREMENTS FOR EACH FINDING:
- issue_id: sequential (PRIV-001, PRIV-002 ...)
- domain: "privacy"
- requirement: the specific legal requirement being tested, citing the jurisdiction
- status: "pass", "fail", "partial", or "not-applicable"
- severity: "critical", "high", "medium", "low", or "info"
- explanation: plain-language explanation with exact clause citation and jurisdiction context
- evidence: list of verbatim contract excerpts supporting the finding
- remediation: specific recommended action or language change, citing the applicable law
- fallback_position: acceptable minimum if full remediation is not achievable
- applicable_laws: specific law/article references, e.g. ["GDPR Art. 28", "DPDPA 2023 §9", "PDPA (TH) s.26"]
- jurisdictions: list of jurisdictions to which this finding applies
- escalate: true if this must be escalated to human counsel
- escalation_target: "HUMAN PRIVACY COUNSEL" or "EXPORT CONTROL TEAM"
- source_page / source_section / source_clause_id / source_excerpt: exact citation
"""


def _export_agent_instructions() -> str:
    return f"""\
You are the Export Control & Sanctions Agent for ClauseGuard, an AI contract compliance review agent
specialising exclusively in Export Control and Sanctions compliance.

IMPORTANT: Export control review was triggered because the contract contains references to
controlled items, technology, encryption, OFAC/EAR/sanctions, or other export triggers.

YOUR TASK:
Review the contract for export control and sanctions compliance. Assign each finding an Issue ID
in the format EXP-001, EXP-002, etc. Set domain = "export_control" on all findings.

If any party, destination, intermediary, beneficial owner, or end user may be sanctioned or
restricted: mark CRITICAL and set escalate = true with escalation_target = "EXPORT CONTROL TEAM".

BASELINE EXPORT CONTROL TESTS:
{_EXPORT_TESTS}

JURISDICTION-SPECIFIC EXPORT CONTROL INSTRUCTIONS:
{_EXPORT_JURISDICTION_INSTRUCTIONS}

HIGH-RISK ITEMS (increase risk by one level, require classification/counsel review if present):
encryption, cyber-surveillance, semiconductors, aerospace, telecom core/network, satellite,
defense, nuclear, chemical, biological, AI model weights, advanced computing

REMOTE ACCESS / DEEMED EXPORT NOTE:
Treat remote support, software updates, cloud access, source-code escrow, model sharing,
engineering collaboration, debug logs with technical data, and access by foreign nationals
as potential export events requiring analysis.

{_OPERATING_RULES}

{_GUARDRAILS}

OUTPUT REQUIREMENTS FOR EACH FINDING:
- issue_id: sequential (EXP-001, EXP-002 ...)
- domain: "export_control"
- requirement: the specific export-control/sanctions requirement being tested
- status: "pass", "fail", "partial", or "not-applicable"
- severity: "critical", "high", "medium", "low", or "info"
- explanation: plain-language explanation with exact clause citation
- evidence: list of verbatim contract excerpts
- remediation: specific recommended action
- fallback_position: acceptable minimum fallback
- applicable_laws: e.g. ["EAR Part 734", "OFAC SDN List", "EU Dual-Use Reg. Art. 3"]
- jurisdictions: list of relevant export-control jurisdictions
- escalate: true if this must be escalated
- escalation_target: "EXPORT CONTROL TEAM"
- source_page / source_section / source_clause_id / source_excerpt: exact citation
"""


def _redline_agent_instructions(export_triggered: bool) -> str:
    export_block = ""
    if export_triggered:
        export_block = f"""
EXPORT CONTROL REDLINE MINIMUM REQUIREMENTS (apply where export control is triggered):
{_EXPORT_REDLINES}
"""
    return f"""\
You are the Redline & Decision Agent for ClauseGuard, an AI contract compliance review agent
specialising exclusively in Data Privacy and Export Control / Sanctions compliance.

YOUR TASK:
1. Propose specific redlines for all unresolved FAIL and HIGH/CRITICAL findings.
2. Issue the final compliance decision for the contract.

PRIVACY REDLINE MINIMUM REQUIREMENTS:
{_PRIVACY_REDLINES}
{export_block}
DECISION LOGIC (apply strictly):
{_DECISION_LOGIC}

REDLINE REQUIREMENTS:
- Provide exact replacement wording where possible.
- If exact wording is not possible, provide a structured drafting instruction.
- Link each redline to its issue_id (e.g. PRIV-001, EXP-002).
- Set domain = "privacy" or "export_control" on each redline.
- Include the applicable_laws driving the redline requirement.

FINAL DECISION REQUIREMENTS:
- outcome: "pass" | "conditional_pass" | "fail" | "escalate"
- rationale: one concise paragraph summarising the main reasons
- conditions: list of specific conditions to resolve (for conditional_pass)
- escalation_targets: list of who must review (for escalate)

NEVER state a contract is 'fully compliant in all jurisdictions'.
Prefer 'no material issues identified on current facts' over categorical legal certification.

{_OPERATING_RULES}

{_GUARDRAILS}
"""


def _clause_analysis_instructions() -> str:
    return """\
You are the Clause Analysis Agent for ClauseGuard, an AI contract compliance review agent
specialising exclusively in Data Privacy and Export Control / Sanctions compliance.

YOUR TASK:
Extract and analyze only the clauses relevant to data privacy and export control.
Focus on: data protection, data processing, cross-border transfers, subprocessors,
breach notification, data subject rights, retention/deletion, security, confidentiality,
export control, sanctions, encryption, and any AI/ML data-use clauses.

For each clause:
- Set domain = "privacy" or "export_control" as appropriate
- Identify applicable_laws (e.g. ["GDPR Art. 28", "EAR §734.13"])
- Assign risk_level using: critical/high/medium/low/info
- Provide actionable recommendations
- Always cite the exact source_section or source_clause_id

If the contract involves AI/ML services, datasets, training data, model weights, telemetry,
or employee monitoring, increase privacy scrutiny by one level.

Return 5–15 significant items covering privacy and export-control clauses only.
"""


def _verification_agent_instructions() -> str:
    return f"""\
You are the Compliance Verification Agent for ClauseGuard, an AI contract compliance review agent.

YOUR TASK:
Review the preliminary compliance findings alongside the provided web search context. For each finding, verify whether the evaluation is legally accurate and on track under the applicable laws and jurisdictions.

CRITICAL INSTRUCTIONS:
1. Confirm, refine, or correct each compliance finding using the real-time search context.
2. If search results confirm the finding is correct, keep it. You may update the `explanation` and `remediation` to incorporate relevant insights, rules, or citations from the search results.
3. If search results indicate the finding is incorrect, a false positive, or legally permitted under the jurisdiction's rules, change its status to "pass" or "not-applicable" (or decrease its severity to "info" and explain why).
4. Update the severity if the search reveals the issue is more or less severe under local regulations.
5. Keep the same `issue_id` for each finding so we can trace it back.
6. Set `domain` correctly to "privacy" or "export_control" for each finding.
7. Return a complete list of all verified/corrected findings.

{_OPERATING_RULES}

{_GUARDRAILS}
"""


# ---------------------------------------------------------------------------
# Main assistant class
# ---------------------------------------------------------------------------

class OpenAILegalAssistant:
    """Async legal assistant for Data Privacy & Export Control compliance review."""

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
        # ------------------------------------------------------------------
        # Step 1: Detect export control trigger
        # ------------------------------------------------------------------
        text_for_detection = document.text or (
            document.content if isinstance(document.content, str) else ""
        )
        export_triggered = detect_export_control_trigger(text_for_detection)
        logger.info(
            "Export control trigger: %s for %s", export_triggered, document.filename
        )

        # ------------------------------------------------------------------
        # Step 2: Run agents (jurisdiction profile + privacy always; export only if triggered)
        # ------------------------------------------------------------------
        agent_tasks: list = [
            # Agent 1 — Jurisdiction Profile
            self._run_agent(
                document=document,
                spec=AgentPromptSpec(
                    role="Jurisdiction Profile Agent",
                    instructions=_jurisdiction_agent_instructions(),
                ),
                schema=JurisdictionProfileResponse,
            ),
            # Agent 2 — Data Privacy Compliance
            self._run_agent(
                document=document,
                spec=AgentPromptSpec(
                    role="Data Privacy Compliance Agent",
                    instructions=_privacy_agent_instructions(),
                ),
                schema=ComplianceAuditResponse,
            ),
            # Agent 3 — Clause Analysis (privacy + export clauses)
            self._run_agent(
                document=document,
                spec=AgentPromptSpec(
                    role="Clause Analysis Agent",
                    instructions=_clause_analysis_instructions(),
                ),
                schema=ClauseAnalysisResponse,
            ),
        ]

        # Add export control agent only if triggered
        if export_triggered:
            agent_tasks.append(
                self._run_agent(
                    document=document,
                    spec=AgentPromptSpec(
                        role="Export Control & Sanctions Agent",
                        instructions=_export_agent_instructions(),
                    ),
                    schema=ComplianceAuditResponse,
                )
            )

        tasks_results = await asyncio.gather(*agent_tasks, return_exceptions=True)

        juris_result = self._unwrap_response(tasks_results[0], JurisdictionProfileResponse)
        privacy_result = self._unwrap_response(tasks_results[1], ComplianceAuditResponse)
        clause_result = self._unwrap_response(tasks_results[2], ClauseAnalysisResponse)

        export_findings: list = []
        if export_triggered and len(tasks_results) > 3:
            export_result = self._unwrap_response(tasks_results[3], ComplianceAuditResponse)
            export_findings = export_result.items

        # ------------------------------------------------------------------
        # Step 3: Merge all compliance findings
        # ------------------------------------------------------------------
        all_findings = list(privacy_result.items) + export_findings

        # ------------------------------------------------------------------
        # Step 3.5: Run Web Search & Compliance Verification Agent
        # ------------------------------------------------------------------
        # Filter findings that are failed/partial and sort them by severity (top 5 max to avoid rate limits)
        findings_to_search = [f for f in all_findings if f.status in ("fail", "partial")]
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
        findings_to_search.sort(key=lambda x: severity_order.get(str(x.severity).lower(), 99))
        findings_to_search = findings_to_search[:5]

        verified_findings = []
        if findings_to_search:
            search_tasks = []
            for f in findings_to_search:
                # Construct a shorter, cleaner query for better search engine results
                law = f.applicable_laws[0] if f.applicable_laws else ""
                jurisdiction = f.jurisdictions[0] if f.jurisdictions else ""
                req_snippet = " ".join(str(f.requirement).split()[:5])
                
                query_parts = []
                if law:
                    query_parts.append(law)
                if jurisdiction:
                    query_parts.append(jurisdiction)
                if req_snippet:
                    query_parts.append(req_snippet)
                query = " ".join(query_parts)
                search_tasks.append(async_web_search(query))
            
            search_results_list = await asyncio.gather(*search_tasks)

            search_blocks = []
            for idx, f in enumerate(findings_to_search):
                res = search_results_list[idx]
                formatted_res = format_search_results(res)
                search_blocks.append(
                    f"--- SEARCH FOR FINDING {f.issue_id} ---\n"
                    f"Finding Requirement: {f.requirement}\n"
                    f"Applicable Laws: {f.applicable_laws}\n"
                    f"Jurisdictions: {f.jurisdictions}\n"
                    f"Search Results:\n{formatted_res}"
                )
            search_context = "\n\n".join(search_blocks)

            verification_payload = DocumentPayload(
                filename=document.filename,
                file_type="text",
                text=(
                    f"ORIGINAL CONTRACT EXCERPT:\n{document.text[:8000]}\n\n"
                    f"PRELIMINARY COMPLIANCE FINDINGS:\n{json.dumps([f.model_dump() for f in all_findings], indent=2)}\n\n"
                    f"WEB SEARCH LEGAL CONTEXT:\n{search_context}"
                ),
                content=(
                    f"ORIGINAL CONTRACT EXCERPT:\n{document.text[:8000]}\n\n"
                    f"PRELIMINARY COMPLIANCE FINDINGS:\n{json.dumps([f.model_dump() for f in all_findings], indent=2)}\n\n"
                    f"WEB SEARCH LEGAL CONTEXT:\n{search_context}"
                ),
                source_context=document.source_context,
            )

            verified_result_raw = await self._run_agent(
                document=verification_payload,
                spec=AgentPromptSpec(
                    role="Compliance Verification Agent",
                    instructions=_verification_agent_instructions(),
                ),
                schema=ComplianceAuditResponse,
            )
            verified_result = self._unwrap_response(verified_result_raw, ComplianceAuditResponse)
            verified_findings_raw = list(verified_result.items)
            
            if verified_findings_raw:
                # Merge verified findings back into the original findings list
                verified_map = {vf.issue_id: vf for vf in verified_findings_raw if vf.issue_id}
                merged_findings = []
                for f in all_findings:
                    if f.issue_id in verified_map:
                        merged_findings.append(verified_map[f.issue_id])
                    else:
                        merged_findings.append(f)
                
                # Append any new verified findings that don't have matching issue_ids
                existing_ids = {f.issue_id for f in all_findings if f.issue_id}
                for vf in verified_findings_raw:
                    if vf.issue_id and vf.issue_id not in existing_ids:
                        merged_findings.append(vf)
                verified_findings = merged_findings
            else:
                logger.warning("Verification agent returned no findings. Falling back to unverified findings.")
                verified_findings = all_findings
        else:
            logger.info("No compliance issues to verify. Skipping web search.")
            verified_findings = all_findings

        # ------------------------------------------------------------------
        # Step 4: Run Redline + Decision agent (with merged context)
        # ------------------------------------------------------------------
        findings_summary = self._build_findings_summary(verified_findings)
        redline_document = DocumentPayload(
            filename=document.filename,
            file_type="text",
            text=(
                f"ORIGINAL CONTRACT:\n{document.text[:8000]}\n\n"
                f"COMPLIANCE FINDINGS SUMMARY:\n{findings_summary}"
            ),
            content=(
                f"ORIGINAL CONTRACT:\n{document.text[:8000]}\n\n"
                f"COMPLIANCE FINDINGS SUMMARY:\n{findings_summary}"
            ),
            source_context=document.source_context,
        )
        redline_result_raw = await self._run_agent(
            document=redline_document,
            spec=AgentPromptSpec(
                role="Redline & Decision Agent",
                instructions=_redline_agent_instructions(export_triggered),
            ),
            schema=RedlineResponse,
        )
        redline_result = self._unwrap_response(redline_result_raw, RedlineResponse)

        # ------------------------------------------------------------------
        # Step 5: Compute safety score and summary
        # ------------------------------------------------------------------
        # Patch jurisdiction_profile with the detected export_triggered flag
        jurisdiction_profile = juris_result.items if isinstance(juris_result, JurisdictionProfileResponse) else JurisdictionProfile()
        jurisdiction_profile = JurisdictionProfile(
            privacy_jurisdictions=jurisdiction_profile.privacy_jurisdictions,
            export_control_jurisdictions=jurisdiction_profile.export_control_jurisdictions,
            export_control_triggered=export_triggered,
            trigger_rationale=jurisdiction_profile.trigger_rationale or (
                "Export control triggered by contract content." if export_triggered
                else "No export-control trigger identified on current facts."
            ),
        )

        safety_score = self._derive_safety_score(verified_findings, clause_result)
        summary = self._derive_summary(
            document=document,
            all_findings=verified_findings,
            final_decision=redline_result.final_decision,
            safety_score=safety_score,
            export_triggered=export_triggered,
        )

        return ContractReviewOutput(
            contract_safety_score=safety_score,
            summary=summary,
            jurisdiction_profile=jurisdiction_profile,
            compliance_findings=verified_findings,
            redline_suggestions=redline_result.redlines,
            final_decision=redline_result.final_decision,
            clause_analyses=clause_result.items,
            export_control_triggered=export_triggered,
            source_filename=document.filename,
            document_type=document.file_type,
        )

    # ------------------------------------------------------------------
    # NDA generation (unchanged)
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_findings_summary(self, findings: list) -> str:
        """Build a concise text summary of all findings for the Redline agent."""
        lines: list[str] = []
        for f in findings:
            domain_label = getattr(f, "domain", "privacy").upper()
            issue_id = getattr(f, "issue_id", "")
            severity = str(getattr(f, "severity", "")).upper()
            status = getattr(f, "status", "")
            req = getattr(f, "requirement", "")
            explanation = getattr(f, "explanation", "")
            escalate = getattr(f, "escalate", False)
            laws = ", ".join(getattr(f, "applicable_laws", [])) or "N/A"
            clause_ref = getattr(f, "source_section", "") or getattr(f, "source_clause_id", "") or "N/A"
            lines.append(
                f"[{domain_label}] {issue_id} | {severity} | {status} | {req}\n"
                f"  Finding: {explanation}\n"
                f"  Laws: {laws} | Clause: {clause_ref}"
                + (f" | ESCALATE: {getattr(f, 'escalation_target', '')}" if escalate else "")
            )
        return "\n\n".join(lines) if lines else "No findings identified."

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
            logger.info(
                "OpenAI request: model=%s, sys_len=%d, user_len=%d",
                model,
                len(system_message),
                len(str(user_content)),
            )
            response = await self.client.chat.completions.create(
                model=model,
                messages=messages,
                response_format={"type": "json_object"},
                temperature=0.2,
            )
            resp_id = getattr(response, "id", None) or (
                response.to_dict().get("id") if hasattr(response, "to_dict") else None
            )
            logger.info("OpenAI response received: id=%s", resp_id)
            content = response.choices[0].message.content or "{}"
            return content.strip()
        except Exception:
            logger.exception("OpenAI request failed for model %s", model)
            raise

    def _parse_model(self, raw_json: str, schema: type):
        try:
            sanitized_json = self._sanitize_json_for_schema(raw_json, schema)
            return schema.model_validate_json(sanitized_json)
        except Exception:
            logger.exception("Failed to parse OpenAI JSON for %s", schema.__name__)
            return schema.model_validate(self._fallback_payload(schema))

    def _sanitize_json_for_schema(self, raw_json: str, schema: type) -> str:
        """Coerce null citation fields to empty strings or default values and strip extra fields before schema validation."""
        try:
            payload = json.loads(raw_json)
        except Exception:
            return raw_json

        payload = self._coerce_payload_for_schema(payload, schema)
        try:
            return json.dumps(payload, ensure_ascii=False)
        except Exception:
            return raw_json

    def _coerce_payload_for_schema(self, payload: Any, schema: Any) -> Any:
        if payload is None:
            return payload

        # Resolve unions
        origin = typing.get_origin(schema)
        if origin is typing.Union or origin is types.UnionType:
            args = typing.get_args(schema)
            non_none_args = [arg for arg in args if arg is not type(None)]
            if len(non_none_args) == 1:
                schema = non_none_args[0]
                origin = typing.get_origin(schema)

        # Handle lists/sequences
        if origin in (list, typing.List, set, typing.Set, tuple, typing.Tuple):
            args = typing.get_args(schema)
            if args:
                item_schema = args[0]
                if isinstance(payload, list):
                    return [self._coerce_payload_for_schema(item, item_schema) for item in payload]

        # Handle Pydantic models
        if isinstance(schema, type) and issubclass(schema, BaseModel):
            if isinstance(payload, dict):
                # Construct a new dict to strip any extra fields not defined in the schema
                payload_copy = {}
                for field_name, field_info in schema.model_fields.items():
                    if field_name in payload:
                        val = payload[field_name]
                        if val is None:
                            # Coerce None
                            if field_info.default_factory is not None and field_info.default_factory is not PydanticUndefined:
                                payload_copy[field_name] = field_info.default_factory()
                            elif field_info.default is not None and field_info.default is not PydanticUndefined:
                                payload_copy[field_name] = field_info.default
                            else:
                                field_type = field_info.annotation
                                field_origin = typing.get_origin(field_type) or field_type
                                if field_origin in (list, typing.List):
                                    payload_copy[field_name] = []
                                elif field_origin is str:
                                    payload_copy[field_name] = ""
                        else:
                            payload_copy[field_name] = self._coerce_payload_for_schema(val, field_info.annotation)
                return payload_copy

        return payload

    def _unwrap_response(self, value: Any, schema: type):
        if isinstance(value, Exception):
            logger.exception("Agent execution failed", exc_info=value)
            return schema.model_validate(self._fallback_payload(schema))
        return value

    def _fallback_payload(self, schema: type) -> dict[str, Any]:
        fallback: dict[str, Any] = {
            "JurisdictionProfileResponse": {
                "items": {
                    "privacy_jurisdictions": [],
                    "export_control_jurisdictions": [],
                    "export_control_triggered": False,
                    "trigger_rationale": "",
                }
            },
            "ComplianceAuditResponse": {"items": []},
            "ClauseAnalysisResponse": {"items": []},
            "MissingProtectionResponse": {"items": []},
            "RedlineResponse": {
                "redlines": [],
                "final_decision": {
                    "outcome": "escalate",
                    "rationale": "Unable to generate redlines and decision from available facts. Manual review required.",
                    "conditions": [],
                    "escalation_targets": ["HUMAN PRIVACY COUNSEL"],
                },
            },
            "RiskAssessmentResponse": {"items": []},
            "NegotiationStrategyResponse": {"items": []},
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
                "compliance_findings": [],
                "redline_suggestions": [],
                "clause_analyses": [],
                "missing_protections": [],
                "risk_assessments": [],
                "negotiation_strategies": [],
                "export_control_triggered": False,
                "source_filename": "",
                "document_type": "contract",
            },
        }
        return fallback.get(schema.__name__, {})

    # ------------------------------------------------------------------
    # Scoring and summary
    # ------------------------------------------------------------------

    def _derive_safety_score(self, all_findings: list, clause_result) -> int:
        score = 100
        for finding in all_findings:
            sev = str(getattr(finding, "severity", "")).lower()
            if sev == "critical":
                score -= 15
            elif sev == "high":
                score -= 8
            elif sev == "medium":
                score -= 4
            elif sev == "low":
                score -= 1
        # Deduct for critical-risk clause analyses
        for clause in clause_result.items:
            risk = str(getattr(clause, "risk_level", "")).lower()
            if risk == "critical":
                score -= 10
            elif risk == "high":
                score -= 5
        return max(0, min(100, score))

    def _derive_summary(
        self,
        document: DocumentPayload,
        all_findings: list,
        final_decision,
        safety_score: int,
        export_triggered: bool,
    ) -> str:
        privacy_findings = [f for f in all_findings if getattr(f, "domain", "privacy") == "privacy"]
        export_findings = [f for f in all_findings if getattr(f, "domain", "privacy") == "export_control"]
        critical = sum(1 for f in all_findings if str(getattr(f, "severity", "")).lower() == "critical")
        high = sum(1 for f in all_findings if str(getattr(f, "severity", "")).lower() == "high")
        escalations = sum(1 for f in all_findings if getattr(f, "escalate", False))

        decision_label = "unknown"
        if final_decision and hasattr(final_decision, "outcome"):
            decision_label = str(final_decision.outcome).replace("_", " ").upper()

        export_note = (
            f" Export Control review was triggered ({len(export_findings)} findings)."
            if export_triggered
            else " No export-control trigger identified on current facts."
        )

        return (
            f"Review of {document.filename} completed. "
            f"Safety score: {safety_score}/100. "
            f"Final decision: {decision_label}. "
            f"{len(privacy_findings)} data privacy findings ({critical} critical, {high} high).{export_note}"
            + (f" {escalations} finding(s) require escalation to human counsel." if escalations else "")
            + " This review is not legal advice and does not constitute regulatory certification."
        )

    # ------------------------------------------------------------------
    # Document loading (unchanged)
    # ------------------------------------------------------------------

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
            {"type": "text", "text": "Analyze this contract image for data privacy and export control compliance."},
            {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{encoded}"}},
        ]

    def _use_vision(self, document: DocumentPayload) -> bool:
        return document.file_type in {"image"} or (
            document.file_type == "pdf" and isinstance(document.content, list)
        )
