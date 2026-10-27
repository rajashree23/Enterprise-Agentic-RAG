import json
from unittest.mock import AsyncMock, patch
from uuid import UUID

import httpx
from fastapi.testclient import TestClient

from agentic_rag.api.app import app


def test_query_api_returns_issue_evidence():
    decomposition = {
        "sub_queries": [
            {"sub_query": "Retrieve issue #123 from acme/payments."},
        ]
    }

    plan = {
        "execution_steps": [
            {
                "step_key": "get-issue",
                "sub_query_id": "sq-1",
                "action": "Retrieve issue details",
                "capability": "github.get_issue",
                "arguments": {
                    "owner": "acme",
                    "repo": "payments",
                    "issue_number": 123,
                },
                "depends_on_step_keys": [],
            }
        ]
    }

    issue_payload = {
        "id": 9001,
        "number": 123,
        "title": "Release payment retry feature",
        "body": "Waiting for migration approval.",
        "state": "open",
        "html_url": "https://github.com/acme/payments/issues/123",
        "user": {"login": "developer-a"},
        "created_at": "2026-10-20T10:00:00Z",
        "updated_at": "2026-10-24T10:00:00Z",
    }

    github_client = AsyncMock()
    github_client.get.return_value = httpx.Response(
        200,
        json=issue_payload,
        request=httpx.Request(
            "GET",
            "https://api.github.com/repos/acme/payments/issues/123",
        ),
    )

    planning_responses = iter(
        [
            json.dumps(decomposition),
            json.dumps(
                {
                    "outcome": "executable",
                    "reason": "The issue identifier is available.",
                    "execution_plan": plan,
                    "clarification_question": None,
                }
            ),
        ]
    )

    async def generate_response(prompt, *, system_prompt=None, response_schema=None):
        planning_response = next(planning_responses, None)

        if planning_response is not None:
            return planning_response

        context = json.loads(
            prompt.split(
                " as JSON:\n",
                maxsplit=1,
            )[1]
        )
        if "assessment" in context:
            return json.dumps(
                {
                    "claims": [
                        {
                            "text": "Migration approval remains pending.",
                            "citations": [
                                {"evidence_id": context["evidence"][0]["evidence_id"]}
                            ],
                        }
                    ],
                    "limitations": [],
                }
            )

        return json.dumps(
            {
                "status": "sufficient",
                "reason": "Mocked assessment for API integration testing.",
                "relevant_evidence_ids": [
                    item["evidence_id"] for item in context["evidence"]
                ],
                "gaps": [],
            }
        )

    with (
        patch(
            "agentic_rag.llm.lm_studio.LMStudioLLM.generate",
            new_callable=AsyncMock,
        ) as generate,
        patch("agentic_rag.tools.github.issue.httpx.AsyncClient") as client_factory,
    ):
        generate.side_effect = generate_response
        client_factory.return_value.__aenter__.return_value = github_client

        with TestClient(app) as client:
            response = client.post(
                "/query",
                json={"query": "Retrieve issue #123 from acme/payments."},
            )

    assert response.status_code == 200
    body = response.json()

    assert len(body["execution_results"]) == 1
    assert len(body["evidence"]) == 1
    assert body["normalization_warnings"] == []

    execution = body["execution_results"][0]
    evidence = body["evidence"][0]

    assert execution["status"] == "SUCCESS"
    assert execution["tool_called"]["tool_id"] == "github.get_issue"

    assert UUID(evidence["evidence_id"]).version == 4
    assert evidence["step_id"] == execution["step_id"]
    assert evidence["sub_query_id"] == execution["sub_query_id"]

    assert evidence["source"]["record_id"] == "9001"
    assert evidence["source"]["url"] == issue_payload["html_url"]
    assert "Waiting for migration approval." in evidence["content"]
    assert evidence["tool_response"][0]["body"] == issue_payload["body"]

    assert body["assessment_error"] is None
    assert body["assessment"]["status"] == "sufficient"
    assert body["assessment"]["relevant_evidence_ids"] == [
        evidence["evidence_id"],
    ]
    assert body["assessment"]["gaps"] == []

    assert generate.await_count == 4
    assert body["synthesis_error"] is None
    assert body["synthesis"]["claims"] == [
        {
            "text": "Migration approval remains pending.",
            "citations": [
                {"evidence_id": evidence["evidence_id"]},
            ],
        }
    ]
    assert body["synthesis"]["limitations"] == []
    github_client.get.assert_awaited_once()
