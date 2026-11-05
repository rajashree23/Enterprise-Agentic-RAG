import json

import pytest

from agentic_rag.models.capability import CapabilityDefinition
from agentic_rag.models.decomposition import QueryDecomposition, SubQuery
from agentic_rag.models.planning import PlanningOutcome
from agentic_rag.planner.llm_planner import LLMQueryPlanner
from agentic_rag.tools.registry import CapabilityRegistry


class FakeTool:
    async def execute(self, request):
        raise AssertionError("The planner test must not execute a tool")


class FakeLLM:
    def __init__(self, response: dict):
        self.response = response

    async def generate(
        self, prompt: str, *, system_prompt=None, response_schema=None
    ) -> str:
        assert "Never invent identifiers or argument values" in system_prompt
        assert "downstream reasoning" in system_prompt
        assert "determine which blockers remain" in system_prompt
        assert response_schema is not None
        return json.dumps(self.response)


def create_registry() -> CapabilityRegistry:
    registry = CapabilityRegistry()
    registry.register(
        CapabilityDefinition(
            name="github.get_issue",
            description="Retrieve a known GitHub issue.",
            arguments={
                "owner": "string",
                "repo": "string",
                "issue_number": "integer",
            },
        ),
        FakeTool(),
    )
    return registry


def create_decomposition() -> QueryDecomposition:
    return QueryDecomposition(
        sub_queries=[
            SubQuery(
                sub_query_id="sq-1",
                sub_query="Retrieve issue 1 from acme/payments.",
            )
        ]
    )


async def test_planner_returns_executable_decision():
    planner = LLMQueryPlanner(
        FakeLLM(
            {
                "outcome": "executable",
                "reason": "The repository and issue number are known.",
                "execution_plan": {
                    "execution_steps": [
                        {
                            "step_key": "get-issue",
                            "sub_query_id": "sq-1",
                            "action": "Retrieve issue details",
                            "capability": "github.get_issue",
                            "arguments": {
                                "owner": "acme",
                                "repo": "payments",
                                "issue_number": 1,
                            },
                            "depends_on_step_keys": [],
                        }
                    ]
                },
                "clarification_question": None,
            }
        ),
        create_registry(),
    )

    decision = await planner.create_planning_decision(create_decomposition())

    assert decision.outcome == PlanningOutcome.EXECUTABLE
    assert decision.plan is not None
    assert decision.plan.execution_steps[0].step_id == "step-1"


async def test_planner_treats_analysis_over_retrieved_records_as_executable():
    planner = LLMQueryPlanner(
        FakeLLM(
            {
                "outcome": "executable",
                "reason": (
                    "GitHub can retrieve the source records; downstream stages "
                    "determine which blockers remain."
                ),
                "execution_plan": {
                    "execution_steps": [
                        {
                            "step_key": "get-issue",
                            "sub_query_id": "sq-1",
                            "action": "Retrieve issue details",
                            "capability": "github.get_issue",
                            "arguments": {
                                "owner": "acme",
                                "repo": "payments",
                                "issue_number": 1,
                            },
                            "depends_on_step_keys": [],
                        }
                    ]
                },
                "clarification_question": None,
            }
        ),
        create_registry(),
    )
    decomposition = QueryDecomposition(
        sub_queries=[
            SubQuery(
                sub_query_id="sq-1",
                sub_query=(
                    "Read issue 1 from acme/payments and determine which "
                    "production blockers remain."
                ),
            )
        ]
    )

    decision = await planner.create_planning_decision(decomposition)

    assert decision.outcome == PlanningOutcome.EXECUTABLE
    assert decision.plan is not None
    assert decision.plan.execution_steps[0].capability == "github.get_issue"


async def test_planner_returns_clarification_decision():
    planner = LLMQueryPlanner(
        FakeLLM(
            {
                "outcome": "clarification_required",
                "reason": "The repository is missing.",
                "execution_plan": None,
                "clarification_question": "Which repository contains issue 1?",
            }
        ),
        create_registry(),
    )

    decision = await planner.create_planning_decision(create_decomposition())

    assert decision.outcome == PlanningOutcome.CLARIFICATION_REQUIRED
    assert decision.plan is None
    assert decision.clarification_question == "Which repository contains issue 1?"


async def test_planner_converts_missing_tool_arguments_to_clarification():
    planner = LLMQueryPlanner(
        FakeLLM(
            {
                "outcome": "executable",
                "reason": "Retrieve issue details.",
                "execution_plan": {
                    "execution_steps": [
                        {
                            "step_key": "get-issue",
                            "sub_query_id": "sq-1",
                            "action": "Retrieve issue details",
                            "capability": "github.get_issue",
                            "arguments": {
                                "owner": "acme",
                                "issue_number": 1,
                            },
                            "depends_on_step_keys": [],
                        }
                    ]
                },
                "clarification_question": None,
            }
        ),
        create_registry(),
    )

    decision = await planner.create_planning_decision(create_decomposition())

    assert decision.outcome == PlanningOutcome.CLARIFICATION_REQUIRED
    assert decision.plan is None
    assert decision.clarification_question is not None
    assert "repo" in decision.clarification_question


async def test_planner_converts_unknown_capability_to_unsupported():
    llm = FakeLLM(
        {
            "outcome": "executable",
            "reason": "Use Slack search.",
            "execution_plan": {
                "execution_steps": [
                    {
                        "step_key": "slack-search",
                        "sub_query_id": "sq-1",
                        "action": "Search Slack",
                        "capability": "slack.search",
                        "arguments": {"query": "incident"},
                        "depends_on_step_keys": [],
                    }
                ]
            },
            "clarification_question": None,
        }
    )
    planner = LLMQueryPlanner(llm, create_registry())

    decision = await planner.create_planning_decision(create_decomposition())

    assert decision.outcome == PlanningOutcome.UNSUPPORTED
    assert "slack.search" in decision.reason


async def test_planner_repairs_invented_analysis_capability_once():
    class RepairingLLM:
        def __init__(self):
            self.responses = iter(
                [
                    {
                        "outcome": "executable",
                        "reason": "Analyze the retrieved issue.",
                        "execution_plan": {
                            "execution_steps": [
                                {
                                    "step_key": "analyze",
                                    "sub_query_id": "sq-1",
                                    "action": "Analyze issue status",
                                    "capability": "internal.analysis",
                                    "arguments": {},
                                    "depends_on_step_keys": [],
                                }
                            ]
                        },
                        "clarification_question": None,
                    },
                    {
                        "outcome": "executable",
                        "reason": "Retrieve the issue for downstream analysis.",
                        "execution_plan": {
                            "execution_steps": [
                                {
                                    "step_key": "get-issue",
                                    "sub_query_id": "sq-1",
                                    "action": "Retrieve issue details",
                                    "capability": "github.get_issue",
                                    "arguments": {
                                        "owner": "acme",
                                        "repo": "payments",
                                        "issue_number": 1,
                                    },
                                    "depends_on_step_keys": [],
                                }
                            ]
                        },
                        "clarification_question": None,
                    },
                ]
            )
            self.prompts = []

        async def generate(
            self,
            prompt: str,
            *,
            system_prompt=None,
            response_schema=None,
        ) -> str:
            self.prompts.append(prompt)
            return json.dumps(next(self.responses))

    llm = RepairingLLM()
    planner = LLMQueryPlanner(llm, create_registry())

    decision = await planner.create_planning_decision(create_decomposition())

    assert decision.outcome == PlanningOutcome.EXECUTABLE
    assert decision.plan is not None
    assert decision.plan.execution_steps[0].capability == "github.get_issue"
    assert len(llm.prompts) == 2
    correction = json.loads(llm.prompts[1].split(" as JSON:\n", maxsplit=1)[1])[
        "correction_context"
    ]
    assert correction["error"] == "Unsupported capability: internal.analysis"
    assert "downstream assessment and synthesis" in correction["instruction"]


@pytest.mark.parametrize("outcome", ["unsupported", "no_tool_required"])
async def test_planner_returns_non_executable_decision(outcome):
    planner = LLMQueryPlanner(
        FakeLLM(
            {
                "outcome": outcome,
                "reason": "No retrieval execution is needed.",
                "execution_plan": None,
                "clarification_question": None,
            }
        ),
        create_registry(),
    )

    decision = await planner.create_planning_decision(create_decomposition())

    assert decision.outcome.value == outcome
    assert decision.plan is None
