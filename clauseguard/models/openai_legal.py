from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from ._compat import StrEnum


class AnalysisSeverity(StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class RiskLevel(StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class DecisionOutcome(StrEnum):
    PASS = "pass"
    CONDITIONAL_PASS = "conditional_pass"
    FAIL = "fail"
    ESCALATE = "escalate"


class SchemaBase(BaseModel):
    model_config = ConfigDict(extra="forbid")


# ---------------------------------------------------------------------------
# Jurisdiction Profile — spec section 2
# ---------------------------------------------------------------------------

class JurisdictionFinding(SchemaBase):
    jurisdiction: str = Field(description="Jurisdiction name, e.g. 'European Union / EEA'.")
    basis: str = Field(description="Why this jurisdiction applies to this contract.")
    privacy_laws: list[str] = Field(
        default_factory=list,
        description="Applicable privacy laws for this jurisdiction.",
    )
    export_laws: list[str] = Field(
        default_factory=list,
        description="Applicable export-control laws for this jurisdiction (if triggered).",
    )


class JurisdictionProfile(SchemaBase):
    privacy_jurisdictions: list[JurisdictionFinding] = Field(
        default_factory=list,
        description="All jurisdictions where privacy laws apply, with basis and applicable laws.",
    )
    export_control_jurisdictions: list[JurisdictionFinding] = Field(
        default_factory=list,
        description="All jurisdictions where export-control laws apply (empty if not triggered).",
    )
    export_control_triggered: bool = Field(
        default=False,
        description="True if export control review was triggered by contract content.",
    )
    trigger_rationale: str = Field(
        default="",
        description="Explanation of why export control was or was not triggered.",
    )


# ---------------------------------------------------------------------------
# Compliance Finding — spec section 3 & 4 (privacy and export control findings)
# ---------------------------------------------------------------------------

class ComplianceFinding(SchemaBase):
    issue_id: str = Field(
        default="",
        description="Sequential issue identifier, e.g. 'PRIV-001' or 'EXP-001'.",
    )
    domain: Literal["privacy", "export_control", "general"] = Field(
        default="privacy",
        description="Whether this finding relates to privacy, export control, or general compliance.",
    )
    requirement: str = Field(description="Policy or legal requirement being audited.")
    status: str = Field(description="Pass, fail, partial, or not-applicable.")
    severity: AnalysisSeverity = Field(description="Severity if the requirement is not met.")
    explanation: str = Field(description="Plain-language explanation of the result.")
    evidence: list[str] = Field(default_factory=list, description="Supporting evidence from the contract.")
    remediation: str = Field(description="Suggested remediation.")
    fallback_position: str = Field(
        default="",
        description="Acceptable fallback if full remediation is not achievable.",
    )
    applicable_laws: list[str] = Field(
        default_factory=list,
        description="Specific law provisions that apply, e.g. ['GDPR Art. 28', 'DPDPA 2023 §9'].",
    )
    jurisdictions: list[str] = Field(
        default_factory=list,
        description="Jurisdictions to which this finding applies, e.g. ['EU', 'India'].",
    )
    escalate: bool = Field(
        default=False,
        description="True if this finding must be escalated to human privacy counsel or export control team.",
    )
    escalation_target: str = Field(
        default="",
        description="Who to escalate to, e.g. 'HUMAN PRIVACY COUNSEL' or 'EXPORT CONTROL TEAM'.",
    )
    source_page: int | None = Field(default=None, ge=1, description="Page number where the compliance issue is sourced.")
    source_section: str = Field(default="", description="Section or heading for the compliance issue.")
    source_clause_id: str = Field(default="", description="Internal clause identifier from the source document.")
    source_excerpt: str = Field(default="", description="Exact excerpt supporting the compliance finding.")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


# ---------------------------------------------------------------------------
# Redline Suggestion — spec section 5
# ---------------------------------------------------------------------------

class RedlineSuggestion(SchemaBase):
    issue_id: str = Field(
        default="",
        description="Links back to a ComplianceFinding issue_id, e.g. 'PRIV-001'.",
    )
    domain: Literal["privacy", "export_control"] = Field(
        default="privacy",
        description="Whether this redline addresses a privacy or export control issue.",
    )
    clause_reference: str = Field(
        description="Clause or section reference in the contract being redlined.",
    )
    applicable_laws: list[str] = Field(
        default_factory=list,
        description="Laws requiring this redline.",
    )
    proposed_wording: str = Field(
        default="",
        description="Exact replacement wording where possible.",
    )
    drafting_instruction: str = Field(
        default="",
        description="Structured drafting instruction if exact wording is not possible.",
    )


# ---------------------------------------------------------------------------
# Final Decision — spec section 6
# ---------------------------------------------------------------------------

class FinalDecision(SchemaBase):
    outcome: DecisionOutcome = Field(
        description="Overall compliance outcome: pass / conditional_pass / fail / escalate.",
    )
    rationale: str = Field(
        description="One concise paragraph summarising the main reasons for the decision.",
    )
    conditions: list[str] = Field(
        default_factory=list,
        description="For conditional_pass: specific conditions that must be met before signature.",
    )
    escalation_targets: list[str] = Field(
        default_factory=list,
        description="For escalate: who must review, e.g. 'HUMAN PRIVACY COUNSEL', 'EXPORT CONTROL TEAM'.",
    )


# ---------------------------------------------------------------------------
# Contract Review Output — master output model
# ---------------------------------------------------------------------------

class ContractReviewOutput(SchemaBase):
    contract_safety_score: int = Field(ge=0, le=100, description="Overall safety score for the contract (0–100).")
    summary: str = Field(description="Executive summary of the contract analysis (spec section 1).")
    # Spec section 2
    jurisdiction_profile: JurisdictionProfile | None = Field(
        default=None,
        description="Identified privacy and export-control jurisdictions with applicable laws.",
    )
    # Spec sections 3 & 4 (domain field distinguishes privacy vs export_control)
    compliance_findings: list[ComplianceFinding] = Field(
        default_factory=list,
        description="All compliance findings: data privacy (domain=privacy) and export control (domain=export_control).",
    )
    # Spec section 5
    redline_suggestions: list[RedlineSuggestion] = Field(
        default_factory=list,
        description="Proposed redlines with exact wording or drafting instructions.",
    )
    # Spec section 6
    final_decision: FinalDecision | None = Field(
        default=None,
        description="Final decision: approve / approve with conditions / reject / escalate.",
    )
    # Supplementary analysis
    clause_analyses: list[ClauseAnalysis] = Field(
        default_factory=list,
        description="Clause-level analyses for key privacy and export control clauses.",
    )
    missing_protections: list[MissingProtection] = Field(
        default_factory=list,
        description="Missing or absent privacy/export-control protections.",
    )
    # Legacy / backward-compatibility fields (kept empty but preserved for schema compatibility)
    risk_assessments: list[RiskAssessment] = Field(default_factory=list)
    negotiation_strategies: list[NegotiationStrategy] = Field(default_factory=list)
    # Metadata
    export_control_triggered: bool = Field(
        default=False,
        description="True if export control review was triggered by contract content.",
    )
    source_filename: str = Field(default="", description="Original filename if known.")
    document_type: str = Field(default="contract", description="Document classification.")


# ---------------------------------------------------------------------------
# Clause Analysis (repurposed to privacy/export focus)
# ---------------------------------------------------------------------------

class ClauseAnalysis(SchemaBase):
    clause_text: str = Field(description="Clause text extracted from the contract.")
    clause_name: str = Field(description="Short human-readable name for the clause.")
    clause_type: str = Field(description="Normalized clause category (e.g. data_protection, data_transfer, export_control).")
    domain: Literal["privacy", "export_control", "general"] = Field(
        default="privacy",
        description="Domain this clause belongs to.",
    )
    summary: str = Field(description="Concise description of what the clause does.")
    risk_level: RiskLevel = Field(description="Risk classification for the clause.")
    impact: str = Field(description="Practical business or legal impact.")
    recommendations: list[str] = Field(default_factory=list, description="Actionable recommendations.")
    applicable_laws: list[str] = Field(
        default_factory=list,
        description="Laws relevant to this clause, e.g. ['GDPR Art. 28'].",
    )
    source_page: int | None = Field(default=None, ge=1, description="Page number where the clause appears.")
    source_section: str = Field(default="", description="Section or heading where the clause appears.")
    source_clause_id: str = Field(default="", description="Internal clause identifier from the source document.")
    source_excerpt: str = Field(default="", description="Exact excerpt that triggered this finding.")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class RiskAssessment(SchemaBase):
    risk_area: str = Field(description="Area of exposure, such as liability or privacy.")
    severity: AnalysisSeverity = Field(description="Severity of the risk finding.")
    issue: str = Field(description="Short description of the issue.")
    rationale: str = Field(description="Why the issue matters.")
    mitigation: str = Field(description="Recommended mitigation approach.")
    source_page: int | None = Field(default=None, ge=1, description="Page number where the issue is sourced.")
    source_section: str = Field(default="", description="Section or heading where the issue appears.")
    source_clause_id: str = Field(default="", description="Internal clause identifier from the source document.")
    source_excerpt: str = Field(default="", description="Exact excerpt that supports the issue.")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class NegotiationStrategy(SchemaBase):
    objective: str = Field(description="Negotiation objective for the clause set.")
    leverage: str = Field(description="Why the position is reasonable or persuasive.")
    proposed_language: str = Field(description="Suggested replacement or addition language.")
    rationale: str = Field(description="Reason the proposed language improves the deal.")
    priority: AnalysisSeverity = Field(description="Priority level for the negotiation point.")
    source_page: int | None = Field(default=None, ge=1, description="Page number where the negotiation point is sourced.")
    source_section: str = Field(default="", description="Section or heading for the negotiation point.")
    source_clause_id: str = Field(default="", description="Internal clause identifier from the source document.")
    source_excerpt: str = Field(default="", description="Exact excerpt that supports the negotiation point.")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class MissingProtection(SchemaBase):
    protection: str = Field(description="Protection that is absent or underpowered.")
    domain: Literal["privacy", "export_control", "general"] = Field(
        default="privacy",
        description="Domain this missing protection belongs to.",
    )
    why_missing: str = Field(description="What is missing or insufficient.")
    risk: str = Field(description="Resulting exposure from the gap.")
    mitigation: str = Field(description="How to close the gap.")
    suggested_clause: str = Field(description="Draft clause language or insertion guidance.")
    applicable_laws: list[str] = Field(
        default_factory=list,
        description="Laws requiring this protection.",
    )
    source_page: int | None = Field(default=None, ge=1, description="Page number where the gap is sourced.")
    source_section: str = Field(default="", description="Section or heading where the gap appears.")
    source_clause_id: str = Field(default="", description="Internal clause identifier from the source document.")
    source_excerpt: str = Field(default="", description="Exact excerpt that supports the gap.")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


# ---------------------------------------------------------------------------
# Response wrappers (used by individual agents)
# ---------------------------------------------------------------------------

class JurisdictionProfileResponse(SchemaBase):
    items: JurisdictionProfile = Field(
        default_factory=lambda: JurisdictionProfile(),
        description="Full jurisdiction profile including privacy and export-control jurisdictions.",
    )


class ComplianceAuditResponse(SchemaBase):
    items: list[ComplianceFinding] = Field(default_factory=list)


class ClauseAnalysisResponse(SchemaBase):
    items: list[ClauseAnalysis] = Field(default_factory=list)


class MissingProtectionResponse(SchemaBase):
    items: list[MissingProtection] = Field(default_factory=list)


class RedlineResponse(SchemaBase):
    redlines: list[RedlineSuggestion] = Field(default_factory=list)
    final_decision: FinalDecision = Field(
        default_factory=lambda: FinalDecision(
            outcome=DecisionOutcome.ESCALATE,
            rationale="Unable to determine final decision from available facts.",
        )
    )


class RiskAssessmentResponse(SchemaBase):
    items: list[RiskAssessment] = Field(default_factory=list)


class NegotiationStrategyResponse(SchemaBase):
    items: list[NegotiationStrategy] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Misc models
# ---------------------------------------------------------------------------

class SafetyScoreResponse(SchemaBase):
    contract_safety_score: int = Field(ge=0, le=100)
    summary: str = Field(description="Concise executive summary of the contract state.")


class NDAGenerationOutput(SchemaBase):
    title: str = Field(description="Generated NDA title.")
    party_a: str = Field(description="First party name.")
    party_b: str = Field(description="Second party name.")
    effective_date: str = Field(description="Effective date or placeholder text.")
    confidentiality_terms: list[str] = Field(default_factory=list)
    mutuality: str = Field(description="Whether the NDA is mutual or unilateral.")
    governing_law: str = Field(description="Suggested governing law.")
    full_text: str = Field(description="Complete drafted NDA text.")


@dataclass(frozen=True)
class AgentPromptSpec:
    role: str
    instructions: str
    model_name: str = "gpt-4o-mini"


def schema_instructions(model: type[SchemaBase]) -> str:
    return (
        "Return only a valid JSON object that matches this schema exactly. "
        "Do not wrap the response in markdown fences. Schema:\n"
        f"{model.model_json_schema()}"
    )
