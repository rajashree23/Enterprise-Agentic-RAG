from fastapi.testclient import TestClient

from agentic_rag.api.app import app

client = TestClient(app)


from fastapi.testclient import TestClient

from agentic_rag.api.app import app

client = TestClient(app)


def test_query_endpoint():
    response = client.post(
        "/query",
        json={"query": "What is the status of Project X?"},
    )

    assert response.status_code == 200

    body = response.json()

    assert len(body["execution_results"]) == 1

    result = body["execution_results"][0]

    assert result["step_id"] == "step-1"
    assert result["sub_query_id"] == "sq-1"
    assert result["status"] == "SUCCESS"


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


def test_query_endpoint_wrong_method():
    response = client.get("/query")

    assert response.status_code == 405
