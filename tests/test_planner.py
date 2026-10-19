from agentic_rag.models.capability import CapabilityDefinition
from agentic_rag.models.decomposition import (
    QueryDecomposition,
    SubQuery,
)
from agentic_rag.models.execution_plan import ExecutionPlan
from agentic_rag.planner.llm_planner import LLMQueryPlanner
from agentic_rag.planner.planner import DeterministicQueryPlanner
from agentic_rag.tools.registry import CapabilityRegistry


class FakeTool:
    async def execute(self, request):
        raise NotImplementedError("FakeTool should not execute in planner tests.")


class FakeLLM:
    async def generate(self, prompt: str) -> str:
        return """
        {
            "execution_steps": [
                {
                    "sub_query_id": "sq-1",
                    "action": "Find project status",
                    "capability": "github.search",
                     "arguments": {
                        "query": "Project X"
                    },
                    "depends_on_sub_query_ids": []
                },
               {
                    "sub_query_id": "sq-2",
                    "action": "Find related Slack discussions",
                    "capability": "slack.search",
                    "arguments": {
                        "query": "related Slack discussions"
                    },
                    "depends_on_sub_query_ids": ["sq-1"]
                }
            ]
        }
        """


def create_test_registry() -> CapabilityRegistry:
    registry = CapabilityRegistry()
    fake_tool = FakeTool()

    registry.register(
        CapabilityDefinition(
            name="github.search",
            description="Search GitHub issues and pull requests.",
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

    return registry


async def test_create_plan():
    decomposition = QueryDecomposition(
        sub_queries=[
            SubQuery(
                sub_query_id="sq-1",
                sub_query="Find Project X status",
            ),
            SubQuery(
                sub_query_id="sq-2",
                sub_query="Find Project X owner",
            ),
        ]
    )

    planner = DeterministicQueryPlanner()

    plan = await planner.create_plan(decomposition)

    assert len(plan.execution_steps) == 2

    assert plan.execution_steps[0].step_id == "step-1"
    assert plan.execution_steps[0].sub_query_id == "sq-1"

    assert plan.execution_steps[1].step_id == "step-2"
    assert plan.execution_steps[1].sub_query_id == "sq-2"


async def test_llm_query_planner():
    decomposition = QueryDecomposition(
        sub_queries=[
            SubQuery(
                sub_query_id="sq-1",
                sub_query="Find project status",
            ),
            SubQuery(
                sub_query_id="sq-2",
                sub_query="Find related Slack discussions",
            ),
        ]
    )

    planner = LLMQueryPlanner(
        FakeLLM(),
        create_test_registry(),
    )

    plan = await planner.create_plan(decomposition)

    assert isinstance(plan, ExecutionPlan)
    assert len(plan.execution_steps) == 2

    first_step = plan.execution_steps[0]
    second_step = plan.execution_steps[1]

    # Verify structured arguments are preserved.
    assert first_step.arguments == {"query": "Project X"}
    assert second_step.arguments == {"query": "related Slack discussions"}

    assert first_step.step_id == "step-1"
    assert first_step.sub_query_id == "sq-1"

    assert first_step.step_id == "step-1"
    assert first_step.sub_query_id == "sq-1"
    assert first_step.capability == "github.search"
    assert first_step.depends_on == []

    assert second_step.step_id == "step-2"
    assert second_step.sub_query_id == "sq-2"
    assert second_step.capability == "slack.search"
    assert second_step.depends_on == ["step-1"]


async def test_llm_query_planner_rejects_unknown_sub_query_id():
    class FakeLLM:
        async def generate(self, prompt: str) -> str:
            return """
            {
                "execution_steps": [
                    {
                        "sub_query_id": "sq-999",
                        "action": "Do something",
                        "capability": "github.search",
                        "arguments": {
                            "query": "Project X"
                        },
                        "depends_on_sub_query_ids": []
                    }
                ]
            }
            """

    decomposition = QueryDecomposition(
        sub_queries=[
            SubQuery(
                sub_query_id="sq-1",
                sub_query="Find project status",
            )
        ]
    )

    planner = LLMQueryPlanner(
        FakeLLM(),
        create_test_registry(),
    )

    try:
        await planner.create_plan(decomposition)
        assert False, "Expected ValueError"
    except ValueError as exc:
        assert "Unknown sub_query_id" in str(exc)


async def test_llm_query_planner_rejects_unknown_dependency():
    class FakeLLM:
        async def generate(self, prompt: str) -> str:
            return """
            {
                "execution_steps": [
                    {
                        "sub_query_id": "sq-1",
                        "action": "Find project status",
                        "capability": "github.search",
                        "arguments": {
                            "query": "Project X"
                        },
                        "depends_on_sub_query_ids": ["sq-999"]
                    }
                ]
            }
            """

    decomposition = QueryDecomposition(
        sub_queries=[
            SubQuery(
                sub_query_id="sq-1",
                sub_query="Find project status",
            )
        ]
    )

    planner = LLMQueryPlanner(
        FakeLLM(),
        create_test_registry(),
    )

    try:
        await planner.create_plan(decomposition)
        assert False, "Expected ValueError"
    except ValueError as exc:
        assert "Unknown dependency sub_query_id" in str(exc)


async def test_llm_query_planner_rejects_missing_execution_step():
    class FakeLLM:
        async def generate(self, prompt: str) -> str:
            return """
            {
                "execution_steps": []
            }
            """

    decomposition = QueryDecomposition(
        sub_queries=[
            SubQuery(
                sub_query_id="sq-1",
                sub_query="Find project status",
            )
        ]
    )

    planner = LLMQueryPlanner(
        FakeLLM(),
        create_test_registry(),
    )

    try:
        await planner.create_plan(decomposition)
        assert False, "Expected ValueError"
    except ValueError as exc:
        assert "cover every sub-query" in str(exc)


async def test_llm_query_planner_rejects_duplicate_execution_steps():
    class FakeLLM:
        async def generate(self, prompt: str) -> str:
            return """
            {
                "execution_steps": [
                    {
                        "sub_query_id": "sq-1",
                        "action": "Find project status",
                        "capability": "github.search",
                        "arguments": {
                            "query": "Project X"
                        },
                        "depends_on_sub_query_ids": []
                    },
                    {
                        "sub_query_id": "sq-1",
                        "action": "Find project status again",
                        "capability": "github.search",
                        "arguments": {
                            "query": "Project X"
                        },
                        "depends_on_sub_query_ids": []
                    }
                ]
            }
            """

    decomposition = QueryDecomposition(
        sub_queries=[
            SubQuery(
                sub_query_id="sq-1",
                sub_query="Find project status",
            )
        ]
    )

    planner = LLMQueryPlanner(
        FakeLLM(),
        create_test_registry(),
    )

    try:
        await planner.create_plan(decomposition)
        assert False, "Expected ValueError"
    except ValueError as exc:
        assert "Duplicate execution steps" in str(exc)
