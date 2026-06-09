from datetime import datetime

from pydantic import BaseModel, Field

from .clause import ClauseType


class ContractMetadata(BaseModel):
    contract_id: str
    filename: str
    upload_timestamp: datetime = Field(default_factory=datetime.utcnow)
    num_pages: int = 1
    num_clauses: int = 0
    clause_types_found: list[ClauseType] = Field(default_factory=list)
    text_length: int = 0
    latest_reviewed_at: datetime | None = None
    latest_review_score: int | None = None
    latest_review_summary: str = ""
    latest_review_id: str | None = None
    latest_review_finding_count: int = 0


class ContractUploadResponse(BaseModel):
    contract_id: str
    filename: str
    num_clauses: int
    clause_types_found: list[ClauseType]
    message: str = "Contract ingested successfully"
