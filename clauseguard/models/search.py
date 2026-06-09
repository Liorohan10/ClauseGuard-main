from pydantic import BaseModel, Field

from .clause import ClauseType


class SearchRequest(BaseModel):
    query: str = Field(description="Search query text")
    clause_types: list[ClauseType] | None = Field(
        default=None, description="Filter by clause types"
    )
    contract_ids: list[str] | None = Field(
        default=None, description="Filter by contract IDs"
    )
    top_k: int = Field(default=10, ge=1, le=100, description="Number of results")


class SearchHit(BaseModel):
    clause_id: str
    contract_id: str
    clause_type: ClauseType
    text: str
    score: float
    section_number: str = ""
    page_number: int = 1
    highlights: list[str] = Field(default_factory=list)


class SearchResponse(BaseModel):
    query: str
    total_hits: int
    hits: list[SearchHit]
