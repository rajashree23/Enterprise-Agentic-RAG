import pytest

from agentic_rag.decomposer.llm_decomposer import LLMQueryDecomposer
from agentic_rag.llm.lm_studio import LMStudioLLM
from agentic_rag.models.capability import CapabilityDefinition
from agentic_rag.models.execution_plan import ExecutionPlan
from agentic_rag.models.query import QueryInput
from agentic_rag.planner.llm_planner import LLMQueryPlanner
from agentic_rag.tools.registry import CapabilityRegistry

pytestmark = pytest.mark.live


class FakeTool:
    async def execute(self, request):
        raise NotImplementedError("FakeTool should not execute in this test.")


def create_test_registry() -> CapabilityRegistry:
    registry = CapabilityRegistry()
    fake_tool = FakeTool()

    registry.register(
        CapabilityDefinition(
            name="github.search",
            description=(
                "Search GitHub issues and pull requests. Results include record "
                "identifiers and each record's current open or closed state."
            ),
            arguments={"query": "string"},
        ),
        fake_tool,
    )

    registry.register(
        CapabilityDefinition(
            name="slack.search",
            description="Search Slack messages and discussions.",
            arguments={"query": "string"},
        ),
        fake_tool,
    )

    registry.register(
        CapabilityDefinition(
            name="notion.search",
            description="Search Notion workspace pages and documents.",
            arguments={"query": "string"},
        ),
        fake_tool,
    )

    return registry


async def test_real_llm_decomposer_and_planner():
    llm = LMStudioLLM(
        temperature=0.0,
    )

    decomposer = LLMQueryDecomposer(llm)
    planner = LLMQueryPlanner(
        llm,
        create_test_registry(),
    )

    query_input = QueryInput(
        query=(
            "Search GitHub repository openai/openai-python for recent pull "
            "requests about the async client."
        )
    )

    decomposition = await decomposer.decompose(query_input)

    assert len(decomposition.sub_queries) >= 1

    sub_query_ids = {sub_query.sub_query_id for sub_query in decomposition.sub_queries}

    assert len(sub_query_ids) == len(decomposition.sub_queries)

    decision = await planner.create_planning_decision(decomposition)
    plan = decision.plan

    assert plan is not None, decision.model_dump_json(indent=2)
    assert isinstance(plan, ExecutionPlan)
    assert {step.sub_query_id for step in plan.execution_steps} == sub_query_ids

    step_ids = {step.step_id for step in plan.execution_steps}

    assert len(step_ids) == len(plan.execution_steps)

    for step in plan.execution_steps:
        assert step.sub_query_id in sub_query_ids
        assert step.action
        assert step.capability in {
            "github.search",
            "slack.search",
            "notion.search",
        }

        for dependency in step.depends_on:
            assert dependency in step_ids
