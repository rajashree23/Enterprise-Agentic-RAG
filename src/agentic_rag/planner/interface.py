from typing import Protocol

from agentic_rag.models.decomposition import QueryDecomposition
from agentic_rag.models.execution_plan import ExecutionPlan


class QueryPlanner(Protocol):
    async def create_plan(
        self,
        decomposition: QueryDecomposition,
    ) -> ExecutionPlan: ...
