from pydantic import BaseModel, Field

from ._compat import StrEnum


class ClauseType(StrEnum):
    # General clause types (retained)
    INDEMNITY = "indemnity"
    LIABILITY_CAP = "liability_cap"
    TERMINATION = "termination"
    CONFIDENTIALITY = "confidentiality"
    IP_ASSIGNMENT = "ip_assignment"
    GOVERNING_LAW = "governing_law"
    DATA_PROTECTION = "data_protection"
    FORCE_MAJEURE = "force_majeure"
    OTHER = "other"
    # Specialized — Data Privacy & Export Control
    EXPORT_CONTROL = "export_control"
    SANCTIONS = "sanctions"
    DATA_TRANSFER = "data_transfer"          # GDPR Chapter V / cross-border transfer clauses
    SUBPROCESSOR = "subprocessor"            # Sub-processor authorization and flow-down
    BREACH_NOTIFICATION = "breach_notification"  # Incident/breach notification obligations
    DATA_SUBJECT_RIGHTS = "data_subject_rights"  # Data subject rights assistance clauses


class ExtractedClause(BaseModel):
    clause_id: str = Field(default="", description="Unique clause identifier")
    contract_id: str = Field(default="", description="Parent contract identifier")
    clause_type: ClauseType
    text: str = Field(description="Full clause text")
    section_number: str = Field(default="", description="Section number if detected")
    page_number: int = Field(default=1, description="Page where clause appears")
    char_offset_start: int = Field(default=0, description="Character offset start in source")
    char_offset_end: int = Field(default=0, description="Character offset end in source")
    confidence: float = Field(default=0.0, ge=0.0, le=1.0, description="Extraction confidence")
