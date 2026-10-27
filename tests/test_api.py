from unittest.mock import patch

from fastapi.testclient import TestClient

from agentic_rag.api.app import app
from agentic_rag.models.decomposition import QueryDecomposition, SubQuery
from agentic_rag.models.execution_plan import (
    ExecutionPlan,
    ExecutionStep,
)
from agentic_rag.models.planning import PlanningDecision, PlanningOutcome

client = TestClient(app)


class FakeDecomposer:
    async def decompose(self, query_input):
        return QueryDecomposition(
            sub_queries=[
                SubQuery(
                    sub_query_id="sq-1",
                    sub_query=query_input.query,
                )
            ]
        )


class FakePlanner:
    async def create_planning_decision(self, decomposition):
        plan = ExecutionPlan(
            execution_steps=[
                ExecutionStep(
                    step_id="step-1",
                    sub_query_id="sq-1",
                    action=decomposition.sub_queries[0].sub_query,
                    capability="default",
                    depends_on=[],
                )
            ]
        )
        return PlanningDecision(
            outcome=PlanningOutcome.EXECUTABLE,
            reason="The deterministic test plan is executable.",
            plan=plan,
        )


def test_query_endpoint():
    with (
        patch(
            "agentic_rag.api.routes.create_decomposer",
            return_value=FakeDecomposer(),
        ),
        patch(
            "agentic_rag.api.routes.create_planner",
            return_value=FakePlanner(),
        ),
    ):
        response = client.post(
            "/query",
            json={"query": "What is the status of Project X?"},
        )

    assert response.status_code == 200

    body = response.json()

    assert len(body["execution_results"]) == 1

    assert all(
        "step_id" in result and "sub_query_id" in result and "status" in result
        for result in body["execution_results"]
    )


def test_query_endpoint_missing_query():
    response = client.post(
        "/query",
        json={"conversation_id": "conv-123"},
    )

    assert response.status_code == 422


def test_query_endpoint_empty_body():
    response = client.post(
        "/query",
        json={},
    )

    assert response.status_code == 422


def test_query_endpoint_blank_query():
    response = client.post(
        "/query",
        json={"query": "   "},
    )

    assert response.status_code == 422


def test_query_endpoint_wrong_method():
    response = client.get("/query")

    assert response.status_code == 405
