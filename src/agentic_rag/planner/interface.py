from typing import Protocol

from agentic_rag.models.decomposition import QueryDecomposition
from agentic_rag.models.evidence_assessment import EvidenceAssessment
from agentic_rag.models.execution_plan import ExecutionPlan


class QueryPlanner(Protocol):
    async def create_plan(
        self,
        decomposition: QueryDecomposition,
    ) -> ExecutionPlan: ...


class QueryReplanner(Protocol):
    async def create_correction_plan(
        self,
        decomposition: QueryDecomposition,
        assessment: EvidenceAssessment,
        previous_plan: ExecutionPlan,
    ) -> ExecutionPlan: ...
