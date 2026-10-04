from agentic_rag.models.execution_plan import ExecutionPlan, ExecutionStep


def test_execution_plan():
    plan = ExecutionPlan(
        execution_steps=[
            ExecutionStep(
                step_id="step-1",
                sub_query_id="sq-1",
                action="Get current project status",
                capability="github",
                depends_on=[],
            ),
            ExecutionStep(
                step_id="step-2",
                sub_query_id="sq-2",
                action="Get outstanding issues",
                capability="github",
                depends_on=[],
            ),
            ExecutionStep(
                step_id="step-3",
                sub_query_id="sq-3",
                action="Synthesize project status",
                capability="synthesis",
                depends_on=["step-1", "step-2"],
            ),
        ]
    )

    assert len(plan.execution_steps) == 3
    assert plan.execution_steps[0].step_id == "step-1"
    assert plan.execution_steps[2].depends_on == ["step-1", "step-2"]
