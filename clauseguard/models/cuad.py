from pydantic import BaseModel, Field

from .clause import ClauseType


class CuadExample(BaseModel):
    example_id: str
    source_contract_id: str
    title: str
    paragraph_index: int = 0
    qas_id: str
    cuad_label: str
    clause_type: ClauseType = ClauseType.OTHER
    question: str
    answer_text: str
    answer_start: int = 0
    answer_end: int = 0
    context: str
    context_excerpt: str = ""
    is_impossible: bool = False
    text: str = Field(default="", description="Combined searchable text for BM25")
    text_embedding: list[float] = Field(default_factory=list)


class CuadSearchRequest(BaseModel):
    query: str = Field(description="Search query text")
    clause_type: ClauseType | None = Field(default=None, description="Optional clause type filter")
    top_k: int = Field(default=5, ge=1, le=20, description="Number of retrieved examples")


class CuadSearchHit(BaseModel):
    example_id: str
    source_contract_id: str
    title: str
    paragraph_index: int = 0
    qas_id: str
    cuad_label: str
    clause_type: ClauseType = ClauseType.OTHER
    question: str
    answer_text: str
    answer_start: int = 0
    answer_end: int = 0
    context_excerpt: str = ""
    score: float = 0.0
    is_impossible: bool = False


class CuadSearchResponse(BaseModel):
    query: str
    total_hits: int
    examples: list[CuadSearchHit]