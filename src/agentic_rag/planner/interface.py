from typing import Protocol

from agentic_rag.models.decomposition import QueryDecomposition
from agentic_rag.models.evidence_assessment import EvidenceAssessment
from agentic_rag.models.execution_plan import ExecutionPlan
from agentic_rag.models.planning import PlanningDecision


class QueryPlanner(Protocol):
    async def create_planning_decision(
        self,
        decomposition: QueryDecomposition,
    ) -> PlanningDecision: ...


class QueryReplanner(Protocol):
    async def create_correction_plan(
        self,
        decomposition: QueryDecomposition,
        assessment: EvidenceAssessment,
        previous_plan: ExecutionPlan,
    ) -> ExecutionPlan: ...
