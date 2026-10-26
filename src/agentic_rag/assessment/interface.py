from typing import Protocol

from agentic_rag.models.decomposition import QueryDecomposition
from agentic_rag.models.evidence import Evidence
from agentic_rag.models.evidence_assessment import EvidenceAssessment
from agentic_rag.models.execution_plan import ExecutionPlan
from agentic_rag.models.execution_result import ExecutionResult
from agentic_rag.models.query import NormalizationWarning, QueryInput


class EvidenceAssessor(Protocol):
    async def assess(
        self,
        *,
        query_input: QueryInput,
        evidence: list[Evidence],
        execution_results: list[ExecutionResult],
        normalization_warnings: list[NormalizationWarning],
        decomposition: QueryDecomposition | None = None,
        plan: ExecutionPlan | None = None,
    ) -> EvidenceAssessment: ...
