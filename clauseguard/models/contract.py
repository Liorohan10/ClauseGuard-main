from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field, field_validator

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
    latest_review_summary: str = ""
    latest_review_id: str | None = None
    latest_review_finding_count: int = 0

    @field_validator("clause_types_found", mode="before")
    @classmethod
    def coerce_clause_types(cls, v: Any) -> list[str]:
        if not isinstance(v, list):
            return []
        valid_values = {t.value for t in ClauseType}
        coerced = []
        for x in v:
            val = str(x.value) if hasattr(x, "value") else str(x)
            if val in valid_values:
                coerced.append(val)
            else:
                coerced.append(ClauseType.OTHER.value)
        return coerced


class ContractUploadResponse(BaseModel):
    contract_id: str
    filename: str
    num_clauses: int
    clause_types_found: list[ClauseType]
    message: str = "Contract ingested successfully"

    @field_validator("clause_types_found", mode="before")
    @classmethod
    def coerce_clause_types(cls, v: Any) -> list[str]:
        if not isinstance(v, list):
            return []
        valid_values = {t.value for t in ClauseType}
        coerced = []
        for x in v:
            val = str(x.value) if hasattr(x, "value") else str(x)
            if val in valid_values:
                coerced.append(val)
            else:
                coerced.append(ClauseType.OTHER.value)
        return coerced

