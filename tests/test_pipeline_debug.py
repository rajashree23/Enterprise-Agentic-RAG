import pytest

from agentic_rag.composition import (
    create_decomposer,
    create_executor,
    create_planner,
    create_registry,
)
from agentic_rag.models.query import QueryInput

pytestmark = pytest.mark.live


@pytest.mark.asyncio
async def test_pipeline_debug():
    query_input = QueryInput(
        query=(
            "Search GitHub repository openai/openai-python for recent pull "
            "requests about the async client."
        )
    )

    # Stage 1: Decompose the user's question.
    decomposer = create_decomposer()
    decomposition = await decomposer.decompose(query_input)

    print("\n=== 1. QUERY DECOMPOSITION ===")
    print(decomposition.model_dump_json(indent=2))

    # Use one registry for planning and execution.
    registry = create_registry()

    # Stage 2: Create an execution plan.
    planner = create_planner(registry)
    decision = await planner.create_planning_decision(decomposition)
    plan = decision.plan
    assert plan is not None, decision.model_dump_json(indent=2)

    print("\n=== 2. EXECUTION PLAN ===")
    print(plan.model_dump_json(indent=2))

    # Stage 3: Execute the plan.
    executor = create_executor(registry)
    results = await executor.execute(plan)

    print("\n=== 3. EXECUTION RESULTS ===")
    print(results.model_dump_json(indent=2))

    # Basic end-to-end checks.
    assert {step.sub_query_id for step in plan.execution_steps} == {
        sub_query.sub_query_id for sub_query in decomposition.sub_queries
    }
    assert len(results.execution_results) == len(plan.execution_steps)
