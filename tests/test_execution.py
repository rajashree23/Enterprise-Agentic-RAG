from agentic_rag.execution.executor import DeterministicExecutionEngine
from agentic_rag.models.execution_plan import ExecutionPlan, ExecutionStep
from agentic_rag.models.execution_result import ExecutionStatus


def test_execution_engine():
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

    engine = DeterministicExecutionEngine()

    results = engine.execute(plan)

    assert len(results.execution_results) == 2

    assert results.execution_results[0].step_id == "step-1"
    assert results.execution_results[0].sub_query_id == "sq-1"
    assert results.execution_results[0].status == ExecutionStatus.SUCCESS

    assert results.execution_results[1].step_id == "step-2"
    assert results.execution_results[1].sub_query_id == "sq-2"
    assert results.execution_results[1].status == ExecutionStatus.SUCCESS
