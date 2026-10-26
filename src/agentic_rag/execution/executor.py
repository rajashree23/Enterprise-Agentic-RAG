import asyncio

from agentic_rag.execution.operation import ExecutionOperation
from agentic_rag.models.execution_plan import ExecutionPlan, ExecutionStep
from agentic_rag.models.execution_result import (
    ExecutionResult,
    ExecutionResults,
    ExecutionStatus,
    ToolCalled,
    ToolError,
)


class DeterministicExecutionEngine:
    def __init__(
        self,
        operation: ExecutionOperation,
        max_retries: int = 2,
        timeout_seconds: float = 30.0,
    ):
        if max_retries < 0:
            raise ValueError("max_retries must be nonnegative")

        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")

        self.operation = operation
        self.max_retries = max_retries
        self.timeout_seconds = timeout_seconds

    async def execute(self, plan: ExecutionPlan) -> ExecutionResults:
        results = []
        completed_steps = set()
        failed_steps = set()
        skipped_steps = set()

        while len(completed_steps) + len(failed_steps) + len(skipped_steps) < len(
            plan.execution_steps
        ):
            ready_steps = []

            for step in plan.execution_steps:
                if step.step_id in completed_steps:
                    continue

                if step.step_id in failed_steps:
                    continue

                if step.step_id in skipped_steps:
                    continue

                if all(dependency in completed_steps for dependency in step.depends_on):
                    ready_steps.append(step)

            if ready_steps:
                step_results = await asyncio.gather(
                    *[self._execute_with_retry(step) for step in ready_steps]
                )

                for step, result in zip(ready_steps, step_results):
                    results.append(result)

                    if result.status == ExecutionStatus.SUCCESS:
                        completed_steps.add(step.step_id)
                    else:
                        failed_steps.add(step.step_id)

                continue

            for step in plan.execution_steps:
                if (
                    step.step_id in completed_steps
                    or step.step_id in failed_steps
                    or step.step_id in skipped_steps
                ):
                    continue

                if any(
                    dependency in failed_steps or dependency in skipped_steps
                    for dependency in step.depends_on
                ):
                    results.append(
                        ExecutionResult(
                            step_id=step.step_id,
                            sub_query_id=step.sub_query_id,
                            status=ExecutionStatus.SKIPPED,
                        )
                    )

                    skipped_steps.add(step.step_id)

            if len(completed_steps) + len(failed_steps) + len(skipped_steps) == len(
                plan.execution_steps
            ):
                break

            raise ValueError("Execution plan contains unresolved dependencies")

        return ExecutionResults(execution_results=results)

    async def _execute_with_retry(
        self,
        step: ExecutionStep,
    ) -> ExecutionResult:
        last_result = ExecutionResult(
            step_id=step.step_id,
            sub_query_id=step.sub_query_id,
            status=ExecutionStatus.FAILED,
        )

        for _ in range(self.max_retries + 1):
            try:
                candidate_result = await asyncio.wait_for(
                    self.operation.execute(step),
                    timeout=self.timeout_seconds,
                )

            except TimeoutError:
                last_result = ExecutionResult(
                    step_id=step.step_id,
                    sub_query_id=step.sub_query_id,
                    status=ExecutionStatus.FAILED,
                    tool_called=ToolCalled(
                        tool_id=step.capability,
                        tool_name=step.capability,
                    ),
                    tool_error=ToolError(
                        error_id="execution_timeout",
                        error_title="Execution timed out",
                        error_msg=(
                            "The execution attempt exceeded "
                            f"{self.timeout_seconds} seconds."
                        ),
                    ),
                )
            else:
                try:
                    self._validate_result_identity(step, candidate_result)
                except ValueError as exc:
                    return ExecutionResult(
                        step_id=step.step_id,
                        sub_query_id=step.sub_query_id,
                        status=ExecutionStatus.FAILED,
                        tool_error=ToolError(
                            error_id="invalid_execution_result",
                            error_title="Invalid execution result",
                            error_msg=str(exc),
                        ),
                    )

                last_result = candidate_result

            if last_result.status == ExecutionStatus.SUCCESS:
                return last_result

        return last_result

    @staticmethod
    def _validate_result_identity(
        step: ExecutionStep,
        result: ExecutionResult,
    ) -> None:
        if result.step_id != step.step_id:
            raise ValueError(
                "Execution result step_id does not match the executed step"
            )

        if result.sub_query_id != step.sub_query_id:
            raise ValueError(
                "Execution result sub_query_id does not match the executed step"
            )

        if (
            result.tool_called is not None
            and result.tool_called.tool_id != step.capability
        ):
            raise ValueError("Execution result does not match the planned capability")
