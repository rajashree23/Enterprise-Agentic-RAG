from agentic_rag.models.execution_plan import ExecutionPlan
from agentic_rag.models.execution_result import (
    ExecutionResult,
    ExecutionResults,
    ExecutionStatus,
)


class DeterministicExecutionEngine:
    def execute(self, plan: ExecutionPlan) -> ExecutionResults:
        results = []

        for step in plan.execution_steps:
            results.append(
                ExecutionResult(
                    step_id=step.step_id,
                    sub_query_id=step.sub_query_id,
                    status=ExecutionStatus.SUCCESS,
                )
            )

        return ExecutionResults(execution_results=results)
