import json

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


def executable_decision(plan_json: str) -> str:
    return json.dumps(
        {
            "outcome": "executable",
            "reason": "The plan is executable.",
            "execution_plan": json.loads(plan_json),
            "clarification_question": None,
        }
    )


class FakeLLM:
    async def generate(
        self, prompt: str, *, system_prompt=None, response_schema=None
    ) -> str:
        return executable_decision("""
        {
            "execution_steps": [
                {
                    "step_key": "github-search",
                    "sub_query_id": "sq-1",
                    "action": "Find project status",
                    "capability": "github.search",
                     "arguments": {
                        "query": "Project X"
                    },
                    "depends_on_step_keys": []
                },
               {
                    "step_key": "slack-search",
                    "sub_query_id": "sq-2",
                    "action": "Find related Slack discussions",
                    "capability": "slack.search",
                    "arguments": {
                        "query": "related Slack discussions"
                    },
                    "depends_on_step_keys": ["github-search"]
                }
            ]
        }
        """)


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


async def test_create_planning_decision():
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

    decision = await planner.create_planning_decision(decomposition)
    plan = decision.plan

    assert plan is not None
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

    decision = await planner.create_planning_decision(decomposition)
    plan = decision.plan

    assert plan is not None
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
        async def generate(
            self, prompt: str, *, system_prompt=None, response_schema=None
        ) -> str:
            return executable_decision("""
            {
                "execution_steps": [
                    {
                        "step_key": "unknown-sub-query",
                        "sub_query_id": "sq-999",
                        "action": "Do something",
                        "capability": "github.search",
                        "arguments": {
                            "query": "Project X"
                        },
                        "depends_on_step_keys": []
                    }
                ]
            }
            """)

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
        await planner.create_planning_decision(decomposition)
        assert False, "Expected ValueError"
    except ValueError as exc:
        assert "Unknown sub_query_id" in str(exc)


async def test_llm_query_planner_rejects_unknown_dependency():
    class FakeLLM:
        async def generate(
            self, prompt: str, *, system_prompt=None, response_schema=None
        ) -> str:
            return executable_decision("""
            {
                "execution_steps": [
                    {
                        "step_key": "search",
                        "sub_query_id": "sq-1",
                        "action": "Find project status",
                        "capability": "github.search",
                        "arguments": {
                            "query": "Project X"
                        },
                        "depends_on_step_keys": ["missing-step"]
                    }
                ]
            }
            """)

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
        await planner.create_planning_decision(decomposition)
        assert False, "Expected ValueError"
    except ValueError as exc:
        assert "Unknown dependency step_key" in str(exc)


async def test_llm_query_planner_rejects_missing_execution_step():
    class FakeLLM:
        async def generate(
            self, prompt: str, *, system_prompt=None, response_schema=None
        ) -> str:
            return executable_decision("""
            {
                "execution_steps": []
            }
            """)

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
        await planner.create_planning_decision(decomposition)
        assert False, "Expected ValueError"
    except ValueError as exc:
        assert "cover every sub-query" in str(exc)


async def test_llm_query_planner_allows_multiple_steps_for_one_sub_query():
    class FakeLLM:
        async def generate(
            self, prompt: str, *, system_prompt=None, response_schema=None
        ) -> str:
            return executable_decision("""
            {
                "execution_steps": [
                    {
                        "step_key": "search",
                        "sub_query_id": "sq-1",
                        "action": "Find project status",
                        "capability": "github.search",
                        "arguments": {
                            "query": "Project X"
                        },
                        "depends_on_step_keys": []
                    },
                    {
                        "step_key": "details",
                        "sub_query_id": "sq-1",
                        "action": "Find project status again",
                        "capability": "github.search",
                        "arguments": {
                            "query": "Project X"
                        },
                        "depends_on_step_keys": ["search"]
                    }
                ]
            }
            """)

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

    decision = await planner.create_planning_decision(decomposition)
    plan = decision.plan

    assert plan is not None
    assert len(plan.execution_steps) == 2
    assert {step.sub_query_id for step in plan.execution_steps} == {"sq-1"}
    assert plan.execution_steps[1].depends_on == ["step-1"]
