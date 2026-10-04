from agentic_rag.models.decomposition import QueryDecomposition, SubQuery
from agentic_rag.planner.planner import create_plan


def test_create_plan():
    decomposition = QueryDecomposition(
        sub_queries=[
            SubQuery(
                sub_query_id="sq-1",
                sub_query="What is the status of Project X?",
            ),
            SubQuery(
                sub_query_id="sq-2",
                sub_query="What are the open issues?",
            ),
        ]
    )

    plan = create_plan(decomposition)

    assert len(plan.execution_steps) == 2

    assert plan.execution_steps[0].step_id == "step-1"
    assert plan.execution_steps[0].sub_query_id == "sq-1"
    assert plan.execution_steps[0].action == "What is the status of Project X?"

    assert plan.execution_steps[1].step_id == "step-2"
    assert plan.execution_steps[1].sub_query_id == "sq-2"
    assert plan.execution_steps[1].action == "What are the open issues?"
