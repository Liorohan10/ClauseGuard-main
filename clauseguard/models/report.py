from pydantic import BaseModel, Field

from .clause import ClauseType
from ._compat import StrEnum


class Severity(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class Finding(BaseModel):
    clause_type: ClauseType
    severity: Severity
    clause_text: str = Field(description="Actual clause text from contract")
    template_text: str = Field(default="", description="Expected template text")
    deviation: str = Field(description="Description of how clause deviates from template")
    risk: str = Field(description="Potential risk from deviation")
    recommendation: str = Field(description="Suggested fix or action")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)


class RiskReport(BaseModel):
    contract_id: str
    contract_filename: str = ""
    overall_risk_score: float = Field(default=0.0, ge=0.0, le=10.0)
    summary: str = ""
    findings: list[Finding] = Field(default_factory=list)
    coverage: dict[str, bool] = Field(
        default_factory=dict,
        description="Map of clause type to whether it was found in contract",
    )
    missing_required_clauses: list[ClauseType] = Field(default_factory=list)
    num_high: int = 0
    num_medium: int = 0
    num_low: int = 0
