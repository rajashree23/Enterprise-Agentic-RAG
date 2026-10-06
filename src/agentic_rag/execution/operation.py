from typing import Protocol

from agentic_rag.models.execution_plan import ExecutionStep
from agentic_rag.models.execution_result import ExecutionResult


class ExecutionOperation(Protocol):
    async def execute(
        self,
        step: ExecutionStep,
    ) -> ExecutionResult: ...
