from agentic_rag.llm.lm_studio import LMStudioLLM
from agentic_rag.models.decomposition import (
    QueryDecomposition,
    SubQuery,
)
from agentic_rag.models.execution_plan import ExecutionPlan
from agentic_rag.planner.llm_planner import LLMQueryPlanner


async def test_llm_query_planner_with_real_llm():
    decomposition = QueryDecomposition(
        sub_queries=[
            SubQuery(
                sub_query_id="sq-1",
                sub_query="Find the current status of Project X",
            ),
            SubQuery(
                sub_query_id="sq-2",
                sub_query="Find recent GitHub pull requests for Project X",
            ),
        ]
    )

    llm = LMStudioLLM(
        temperature=0.0,
    )

    planner = LLMQueryPlanner(llm)

    plan = await planner.create_plan(decomposition)

    assert isinstance(plan, ExecutionPlan)
    assert len(plan.execution_steps) >= 1

    known_sub_query_ids = {
        sub_query.sub_query_id for sub_query in decomposition.sub_queries
    }

    known_step_ids = {step.step_id for step in plan.execution_steps}

    for step in plan.execution_steps:
        assert step.sub_query_id in known_sub_query_ids
        assert step.step_id
        assert step.action
        assert step.capability

        for dependency in step.depends_on:
            assert dependency in known_step_ids
