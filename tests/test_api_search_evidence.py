import json
from unittest.mock import AsyncMock, patch
from uuid import UUID

import httpx
import pytest
from fastapi.testclient import TestClient

from agentic_rag.api.app import app


@pytest.mark.parametrize(
    ("has_matches", "incomplete"),
    [
        (True, False),
        (True, True),
        (False, False),
    ],
    ids=["matches", "incomplete-search", "no-matches"],
)
def test_search_api_preserves_evidence_and_metadata(
    has_matches,
    incomplete,
):
    query = "Search acme/payments issues about migration approval."

    decomposition = {
        "sub_queries": [
            {"sub_query": query},
        ]
    }

    plan = {
        "execution_steps": [
            {
                "step_key": "search-issues",
                "sub_query_id": "sq-1",
                "action": "Search relevant issues",
                "capability": "github.search",
                "arguments": {
                    "query": "repo:acme/payments is:issue migration",
                },
                "depends_on_step_keys": [],
            }
        ]
    }

    issue = {
        "id": 9001,
        "repository_url": "https://api.github.com/repos/acme/payments",
        "number": 123,
        "title": "Release payment retry feature",
        "body": "Waiting for migration approval.",
        "state": "open",
        "html_url": "https://github.com/acme/payments/issues/123",
        "user": {"login": "developer-a"},
        "created_at": "2026-10-20T10:00:00Z",
        "updated_at": "2026-10-24T10:00:00Z",
    }

    total_count = 18 if has_matches else 0
    search_payload = {
        "total_count": total_count,
        "incomplete_results": incomplete,
        "items": [issue] if has_matches else [],
    }

    github_client = AsyncMock()
    github_client.get.return_value = httpx.Response(
        200,
        json=search_payload,
        request=httpx.Request(
            "GET",
            "https://api.github.com/search/issues",
        ),
    )

    planning_responses = iter(
        [
            json.dumps(decomposition),
            json.dumps(
                {
                    "outcome": "executable",
                    "reason": "The repository and search terms are available.",
                    "execution_plan": plan,
                    "clarification_question": None,
                }
            ),
            *(
                [
                    json.dumps(
                        {
                            "execution_steps": [
                                {
                                    "step_key": "broader-search",
                                    "sub_query_id": "sq-1",
                                    "action": "Retry search with a broader query",
                                    "capability": "github.search",
                                    "arguments": {
                                        "query": (
                                            "repo:acme/payments migration approval"
                                        ),
                                    },
                                    "depends_on_step_keys": [],
                                }
                            ]
                        }
                    )
                ]
                if not has_matches
                else []
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

        # Fourth LLM call: generate claims with citations.
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

        # Third LLM call: assess the retrieved evidence.
        metadata = context["execution_results"][0]["tool_metadata"]

        assert metadata["total_count"] == total_count
        assert metadata["incomplete_results"] is incomplete

        return json.dumps(
            {
                "status": "partial",
                "reason": "Only a subset of matching records was retrieved.",
                "relevant_evidence_ids": [
                    item["evidence_id"] for item in context["evidence"]
                ],
                "gaps": ["Additional matching issues were not retrieved."],
            }
        )

    with (
        patch(
            "agentic_rag.llm.lm_studio.LMStudioLLM.generate",
            new_callable=AsyncMock,
        ) as generate,
        patch("agentic_rag.tools.github.search.httpx.AsyncClient") as client_factory,
    ):
        generate.side_effect = generate_response
        client_factory.return_value.__aenter__.return_value = github_client

        with TestClient(app) as client:
            response = client.post(
                "/query",
                json={"query": query},
            )

    assert response.status_code == 200
    body = response.json()

    assert len(body["execution_results"]) == 1
    execution = body["execution_results"][0]

    assert execution["status"] == "SUCCESS"
    assert execution["tool_called"]["tool_id"] == "github.search"
    assert execution["tool_metadata"] == {
        "total_count": total_count,
        "incomplete_results": incomplete,
    }

    assert body["normalization_warnings"] == []
    assert body["assessment_error"] is None
    assert body["synthesis_error"] is None

    if has_matches:
        assert len(body["evidence"]) == 1
        evidence = body["evidence"][0]

        assert UUID(evidence["evidence_id"]).version == 4
        assert evidence["step_id"] == execution["step_id"]
        assert evidence["sub_query_id"] == execution["sub_query_id"]
        assert evidence["tool_called"]["tool_id"] == "github.search"

        assert evidence["source"]["url"] == issue["html_url"]
        assert evidence["source"]["record_id"] == "9001"
        assert "Waiting for migration approval." in evidence["content"]

        assert body["assessment"]["status"] == "partial"
        assert body["assessment"]["relevant_evidence_ids"] == [
            evidence["evidence_id"],
        ]
        assert body["assessment"]["gaps"] == [
            "Additional matching issues were not retrieved.",
        ]

        assert body["synthesis"]["claims"] == [
            {
                "text": "Migration approval remains pending.",
                "citations": [
                    {"evidence_id": evidence["evidence_id"]},
                ],
            }
        ]
        assert body["synthesis"]["limitations"] == [
            "Additional matching issues were not retrieved.",
            "The available evidence supports only a partial answer.",
        ]

        assert generate.await_count == 4
    else:
        assert execution["tool_response"] == []
        assert body["evidence"] == []

        assert body["assessment"]["status"] == "insufficient"
        assert body["assessment"]["relevant_evidence_ids"] == []
        assert body["assessment"]["gaps"]

        assert body["synthesis"] is None
        assert generate.await_count == 3

    expected_search_calls = 2 if not has_matches else 1
    assert github_client.get.await_count == expected_search_calls
