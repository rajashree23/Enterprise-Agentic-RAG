from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class AssessmentStatus(StrEnum):
    SUFFICIENT = "sufficient"
    PARTIAL = "partial"
    INSUFFICIENT = "insufficient"


class EvidenceAssessment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: AssessmentStatus
    reason: str = Field(min_length=1)
    relevant_evidence_ids: list[str]
    gaps: list[str]
