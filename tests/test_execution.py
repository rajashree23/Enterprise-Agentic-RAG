import asyncio

from agentic_rag.execution.executor import DeterministicExecutionEngine
from agentic_rag.execution.operations import DeterministicExecutionOperation
from agentic_rag.models.execution_plan import ExecutionPlan, ExecutionStep
from agentic_rag.models.execution_result import ExecutionResult, ExecutionStatus


class RecordingExecutionOperation:
    def __init__(self, events):
        self.events = events

    async def execute(self, step):
        self.events.append(f"{step.step_id}-started")

        await asyncio.sleep(0.1)

        self.events.append(f"{step.step_id}-finished")

        return ExecutionResult(
            step_id=step.step_id,
            sub_query_id=step.sub_query_id,
            status=ExecutionStatus.SUCCESS,
        )


class FailingExecutionOperation:
    async def execute(self, step):
        if step.step_id == "step-2":
            return ExecutionResult(
                step_id=step.step_id,
                sub_query_id=step.sub_query_id,
                status=ExecutionStatus.FAILED,
            )

        return ExecutionResult(
            step_id=step.step_id,
            sub_query_id=step.sub_query_id,
            status=ExecutionStatus.SUCCESS,
        )


class RetryExecutionOperation:
    def __init__(self):
        self.attempts = 0

    async def execute(self, step):
        self.attempts += 1

        if self.attempts == 1:
            return ExecutionResult(
                step_id=step.step_id,
                sub_query_id=step.sub_query_id,
                status=ExecutionStatus.FAILED,
            )

        return ExecutionResult(
            step_id=step.step_id,
            sub_query_id=step.sub_query_id,
            status=ExecutionStatus.SUCCESS,
        )


class SlowExecutionOperation:
    async def execute(self, step):
        await asyncio.sleep(1)

        return ExecutionResult(
            step_id=step.step_id,
            sub_query_id=step.sub_query_id,
            status=ExecutionStatus.SUCCESS,
        )


async def test_execution_respects_dependencies():
    plan = ExecutionPlan(
        execution_steps=[
            ExecutionStep(
                step_id="step-3",
                sub_query_id="sq-3",
                action="Summarize Project X",
                capability="default",
                depends_on=["step-1", "step-2"],
            ),
            ExecutionStep(
                step_id="step-1",
                sub_query_id="sq-1",
                action="Find Project X status",
                capability="default",
                depends_on=[],
            ),
            ExecutionStep(
                step_id="step-2",
                sub_query_id="sq-2",
                action="Find Project X owner",
                capability="default",
                depends_on=[],
            ),
        ]
    )

    operation = DeterministicExecutionOperation()
    engine = DeterministicExecutionEngine(operation)

    results = await engine.execute(plan)

    assert len(results.execution_results) == 3

    assert results.execution_results[0].step_id == "step-1"
    assert results.execution_results[1].step_id == "step-2"
    assert results.execution_results[2].step_id == "step-3"


async def test_execution_runs_independent_steps_in_parallel():
    events = []

    operation = RecordingExecutionOperation(events)
    engine = DeterministicExecutionEngine(operation)

    plan = ExecutionPlan(
        execution_steps=[
            ExecutionStep(
                step_id="step-1",
                sub_query_id="sq-1",
                action="Find Project X status",
                capability="default",
                depends_on=[],
            ),
            ExecutionStep(
                step_id="step-2",
                sub_query_id="sq-2",
                action="Find Project X owner",
                capability="default",
                depends_on=[],
            ),
        ]
    )

    await engine.execute(plan)

    assert events == [
        "step-1-started",
        "step-2-started",
        "step-1-finished",
        "step-2-finished",
    ]


async def test_execution_propagates_operation_failure():
    operation = FailingExecutionOperation()
    engine = DeterministicExecutionEngine(operation)

    plan = ExecutionPlan(
        execution_steps=[
            ExecutionStep(
                step_id="step-1",
                sub_query_id="sq-1",
                action="Find Project X status",
                capability="default",
                depends_on=[],
            ),
            ExecutionStep(
                step_id="step-2",
                sub_query_id="sq-2",
                action="Find Project X owner",
                capability="default",
                depends_on=[],
            ),
        ]
    )

    results = await engine.execute(plan)

    assert len(results.execution_results) == 2
    assert results.execution_results[0].status == ExecutionStatus.SUCCESS
    assert results.execution_results[1].status == ExecutionStatus.FAILED


async def test_execution_skips_step_with_failed_dependency():
    operation = FailingExecutionOperation()
    engine = DeterministicExecutionEngine(operation)

    plan = ExecutionPlan(
        execution_steps=[
            ExecutionStep(
                step_id="step-1",
                sub_query_id="sq-1",
                action="Find Project X status",
                capability="default",
                depends_on=[],
            ),
            ExecutionStep(
                step_id="step-2",
                sub_query_id="sq-2",
                action="Find Project X owner",
                capability="default",
                depends_on=[],
            ),
            ExecutionStep(
                step_id="step-3",
                sub_query_id="sq-3",
                action="Summarize Project X",
                capability="default",
                depends_on=["step-2"],
            ),
        ]
    )

    results = await engine.execute(plan)

    assert len(results.execution_results) == 3

    assert results.execution_results[0].step_id == "step-1"
    assert results.execution_results[0].status == ExecutionStatus.SUCCESS

    assert results.execution_results[1].step_id == "step-2"
    assert results.execution_results[1].status == ExecutionStatus.FAILED

    assert results.execution_results[2].step_id == "step-3"
    assert results.execution_results[2].status == ExecutionStatus.SKIPPED


async def test_execution_retries_failed_step():
    operation = RetryExecutionOperation()
    engine = DeterministicExecutionEngine(operation)

    plan = ExecutionPlan(
        execution_steps=[
            ExecutionStep(
                step_id="step-1",
                sub_query_id="sq-1",
                action="Find Project X status",
                capability="default",
                depends_on=[],
            ),
        ]
    )

    results = await engine.execute(plan)

    assert operation.attempts == 2
    assert results.execution_results[0].status == ExecutionStatus.SUCCESS


async def test_execution_times_out_slow_step():
    operation = SlowExecutionOperation()

    engine = DeterministicExecutionEngine(
        operation,
        timeout_seconds=0.1,
    )

    plan = ExecutionPlan(
        execution_steps=[
            ExecutionStep(
                step_id="step-1",
                sub_query_id="sq-1",
                action="Find Project X status",
                capability="default",
                depends_on=[],
            ),
        ]
    )

    results = await engine.execute(plan)

    assert results.execution_results[0].status == ExecutionStatus.FAILED
