from typing import Protocol

from agentic_rag.models.evidence import Evidence
from agentic_rag.models.evidence_assessment import EvidenceAssessment
from agentic_rag.models.query import QueryInput
from agentic_rag.models.synthesis import Synthesis


class AnswerSynthesizer(Protocol):
    async def synthesize(
        self,
        *,
        query_input: QueryInput,
        assessment: EvidenceAssessment,
        evidence: list[Evidence],
    ) -> Synthesis: ...
