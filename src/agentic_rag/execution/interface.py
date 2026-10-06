from typing import Protocol

from agentic_rag.models.execution_plan import ExecutionPlan
from agentic_rag.models.execution_result import ExecutionResults


class ExecutionEngine(Protocol):
    async def execute(self, plan: ExecutionPlan) -> ExecutionResults: ...
