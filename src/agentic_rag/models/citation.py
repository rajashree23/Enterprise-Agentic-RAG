from pydantic import BaseModel, ConfigDict, Field

from agentic_rag.models.evidence import EvidenceSource


class ResolvedCitation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    evidence_id: str = Field(min_length=1)
    source: EvidenceSource
