from agentic_rag.models.execution_plan import ExecutionStep
from agentic_rag.models.execution_result import (
    ExecutionResult,
    ExecutionStatus,
)


class DeterministicExecutionOperation:
    async def execute(
        self,
        step: ExecutionStep,
    ) -> ExecutionResult:
        return ExecutionResult(
            step_id=step.step_id,
            sub_query_id=step.sub_query_id,
            status=ExecutionStatus.SUCCESS,
        )
