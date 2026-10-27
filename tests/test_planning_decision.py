import pytest
from pydantic import ValidationError

from agentic_rag.models.execution_plan import ExecutionPlan, ExecutionStep
from agentic_rag.models.planning import (
    LLMPlanningDecision,
    PlanningDecision,
    PlanningOutcome,
)


@pytest.fixture
def executable_plan():
    return ExecutionPlan(
        execution_steps=[
            ExecutionStep(
                step_id="step-1",
                sub_query_id="sq-1",
                action="Retrieve issue details",
                capability="github.get_issue",
                arguments={
                    "owner": "acme",
                    "repo": "payments",
                    "issue_number": 1,
                },
                depends_on=[],
            )
        ]
    )


def test_executable_decision_accepts_plan(executable_plan):
    decision = PlanningDecision(
        outcome=PlanningOutcome.EXECUTABLE,
        reason="All required arguments are available.",
        plan=executable_plan,
    )

    assert decision.plan == executable_plan
    assert decision.clarification_question is None


@pytest.mark.parametrize(
    "outcome",
    [
        PlanningOutcome.UNSUPPORTED,
        PlanningOutcome.NO_TOOL_REQUIRED,
    ],
)
def test_non_executable_decisions_do_not_contain_plan(outcome):
    decision = PlanningDecision(
        outcome=outcome,
        reason="No executable retrieval plan is needed.",
    )

    assert decision.plan is None


def test_clarification_decision_accepts_question():
    decision = PlanningDecision(
        outcome=PlanningOutcome.CLARIFICATION_REQUIRED,
        reason="The repository is missing.",
        clarification_question="Which repository contains issue 123?",
    )

    assert decision.clarification_question == "Which repository contains issue 123?"


def test_executable_decision_requires_plan():
    with pytest.raises(
        ValidationError,
        match="Executable planning decisions require a plan",
    ):
        PlanningDecision(
            outcome=PlanningOutcome.EXECUTABLE,
            reason="The request can be executed.",
        )


def test_clarification_decision_requires_question():
    with pytest.raises(
        ValidationError,
        match="Clarification decisions require a clarification question",
    ):
        PlanningDecision(
            outcome=PlanningOutcome.CLARIFICATION_REQUIRED,
            reason="The repository is missing.",
        )


def test_non_executable_decision_rejects_plan(executable_plan):
    with pytest.raises(
        ValidationError,
        match="Only executable planning decisions may contain an execution plan",
    ):
        PlanningDecision(
            outcome=PlanningOutcome.UNSUPPORTED,
            reason="This capability is unavailable.",
            plan=executable_plan,
        )


def test_llm_non_executable_decision_accepts_empty_plan():
    decision = LLMPlanningDecision(
        outcome=PlanningOutcome.UNSUPPORTED,
        reason="The capability is not available.",
        execution_plan={"execution_steps": []},
        clarification_question=None,
    )

    assert decision.execution_plan is None
