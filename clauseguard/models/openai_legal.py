from __future__ import annotations

from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict, Field

from ._compat import StrEnum


class AnalysisSeverity(StrEnum):
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


class SchemaBase(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ClauseAnalysis(SchemaBase):
    clause_text: str = Field(description="Clause text extracted from the contract.")
    clause_name: str = Field(description="Short human-readable name for the clause.")
    clause_type: str = Field(description="Normalized clause category or clause family.")
    summary: str = Field(description="Concise description of what the clause does.")
    risk_level: RiskLevel = Field(description="Risk classification for the clause.")
    impact: str = Field(description="Practical business or legal impact.")
    recommendations: list[str] = Field(default_factory=list, description="Actionable recommendations.")
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


class ComplianceFinding(SchemaBase):
    requirement: str = Field(description="Policy or legal requirement being audited.")
    status: str = Field(description="Pass, fail, partial, or not-applicable.")
    severity: AnalysisSeverity = Field(description="Severity if the requirement is not met.")
    explanation: str = Field(description="Plain-language explanation of the result.")
    evidence: list[str] = Field(default_factory=list, description="Supporting evidence from the contract.")
    remediation: str = Field(description="Suggested remediation.")
    source_page: int | None = Field(default=None, ge=1, description="Page number where the compliance issue is sourced.")
    source_section: str = Field(default="", description="Section or heading for the compliance issue.")
    source_clause_id: str = Field(default="", description="Internal clause identifier from the source document.")
    source_excerpt: str = Field(default="", description="Exact excerpt supporting the compliance finding.")
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
    why_missing: str = Field(description="What is missing or insufficient.")
    risk: str = Field(description="Resulting exposure from the gap.")
    mitigation: str = Field(description="How to close the gap.")
    suggested_clause: str = Field(description="Draft clause language or insertion guidance.")
    source_page: int | None = Field(default=None, ge=1, description="Page number where the gap is sourced.")
    source_section: str = Field(default="", description="Section or heading where the gap appears.")
    source_clause_id: str = Field(default="", description="Internal clause identifier from the source document.")
    source_excerpt: str = Field(default="", description="Exact excerpt that supports the gap.")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class ContractReviewOutput(SchemaBase):
    contract_safety_score: int = Field(ge=0, le=100, description="Overall safety score for the contract.")
    summary: str = Field(description="Executive summary of the contract analysis.")
    clause_analyses: list[ClauseAnalysis] = Field(default_factory=list)
    risk_assessments: list[RiskAssessment] = Field(default_factory=list)
    compliance_findings: list[ComplianceFinding] = Field(default_factory=list)
    negotiation_strategies: list[NegotiationStrategy] = Field(default_factory=list)
    missing_protections: list[MissingProtection] = Field(default_factory=list)
    source_filename: str = Field(default="", description="Original filename if known.")
    document_type: str = Field(default="contract", description="Document classification.")


class ClauseAnalysisResponse(SchemaBase):
    items: list[ClauseAnalysis] = Field(default_factory=list)


class RiskAssessmentResponse(SchemaBase):
    items: list[RiskAssessment] = Field(default_factory=list)


class ComplianceAuditResponse(SchemaBase):
    items: list[ComplianceFinding] = Field(default_factory=list)


class NegotiationStrategyResponse(SchemaBase):
    items: list[NegotiationStrategy] = Field(default_factory=list)


class MissingProtectionResponse(SchemaBase):
    items: list[MissingProtection] = Field(default_factory=list)


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
