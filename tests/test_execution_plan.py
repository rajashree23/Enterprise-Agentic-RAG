from agentic_rag.models.execution_plan import (
    ExecutionPlan,
    ExecutionStep,
    LLMExecutionPlan,
)


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


def test_llm_execution_plan_supports_multiple_steps_per_sub_query():
    plan = LLMExecutionPlan.model_validate(
        {
            "execution_steps": [
                {
                    "step_key": "search",
                    "sub_query_id": "sq-1",
                    "action": "Search for the issue",
                    "capability": "github.search",
                    "arguments": {"query": "Project X"},
                    "depends_on_step_keys": [],
                },
                {
                    "step_key": "comments",
                    "sub_query_id": "sq-1",
                    "action": "Read issue comments",
                    "capability": "github.list_issue_comments",
                    "arguments": {"owner": "acme", "repo": "x", "issue_number": 1},
                    "depends_on_step_keys": ["search"],
                },
            ]
        }
    )

    assert [step.step_key for step in plan.execution_steps] == ["search", "comments"]
    assert plan.execution_steps[1].depends_on_step_keys == ["search"]
