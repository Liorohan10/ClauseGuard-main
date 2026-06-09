from pydantic import BaseModel, Field

from .clause import ClauseType


class ClauseTemplate(BaseModel):
    clause_type: ClauseType
    name: str
    template_text: str = Field(description="Company-approved clause text")
    key_requirements: list[str] = Field(description="Checklist of required elements")
    required: bool = Field(default=True, description="Whether clause must be present")
