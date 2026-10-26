from unittest.mock import AsyncMock, patch
from uuid import uuid4

import httpx
import pytest

from agentic_rag.composition import create_registry
from agentic_rag.execution.tool_operation import ToolExecutionOperation
from agentic_rag.models.execution_plan import ExecutionStep
from agentic_rag.models.execution_result import ExecutionStatus
from agentic_rag.models.tool import ToolRequest
from agentic_rag.tools.github.issue import GitHubIssueTool


@pytest.fixture
def issue_payload():
    return {
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


@pytest.fixture
def github_client():
    client = AsyncMock()

    with patch("agentic_rag.tools.github.issue.httpx.AsyncClient") as factory:
        factory.return_value.__aenter__.return_value = client
        yield client


@pytest.mark.asyncio
async def test_registered_issue_tool_returns_execution_result(
    github_client,
    issue_payload,
):
    url = "https://api.github.com/repos/acme/payments/issues/123"
    github_client.get.return_value = httpx.Response(
        200,
        json=issue_payload,
        request=httpx.Request("GET", url),
    )

    step = ExecutionStep(
        step_id=str(uuid4()),
        sub_query_id=str(uuid4()),
        action="Retrieve issue details",
        capability="github.get_issue",
        arguments={
            "owner": "acme",
            "repo": "payments",
            "issue_number": 123,
        },
        depends_on=[],
    )

    operation = ToolExecutionOperation(create_registry())
    result = await operation.execute(step)

    assert result.status == ExecutionStatus.SUCCESS
    assert result.step_id == step.step_id
    assert result.sub_query_id == step.sub_query_id
    assert result.tool_called.tool_id == "github.get_issue"

    record = result.tool_response[0]

    assert record["id"] == 9001
    assert record["body"] == "Waiting for migration approval."
    assert record["url"] == issue_payload["html_url"]
    assert record["repository"] == "acme/payments"
    assert record["record_type"] == "issue"
    assert result.tool_error is None

    assert github_client.get.call_args.args[0] == url


@pytest.mark.asyncio
async def test_issue_tool_reports_not_found(github_client):
    url = "https://api.github.com/repos/acme/payments/issues/123"
    github_client.get.return_value = httpx.Response(
        404,
        request=httpx.Request("GET", url),
    )

    result = await GitHubIssueTool().execute(
        ToolRequest(
            capability="github.get_issue",
            arguments={
                "owner": "acme",
                "repo": "payments",
                "issue_number": 123,
            },
        )
    )

    assert result.success is False
    assert result.error == "GitHub API returned HTTP 404"


@pytest.mark.asyncio
async def test_invalid_arguments_do_not_call_github(github_client):
    result = await GitHubIssueTool().execute(
        ToolRequest(
            capability="github.get_issue",
            arguments={
                "owner": "acme",
                "repo": "payments",
                "issue_number": "123",
            },
        )
    )

    assert result.success is False
    assert result.error == "Invalid GitHub issue arguments"
    github_client.get.assert_not_awaited()


@pytest.mark.asyncio
async def test_issue_tool_handles_network_failure(github_client):
    github_client.get.side_effect = httpx.ConnectError("Connection unavailable")

    result = await GitHubIssueTool().execute(
        ToolRequest(
            capability="github.get_issue",
            arguments={
                "owner": "acme",
                "repo": "payments",
                "issue_number": 123,
            },
        )
    )

    assert result.success is False
    assert result.error == "GitHub request failed: ConnectError"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload",
    [
        [],
        {},
        {"user": "unexpected string"},
    ],
    ids=["wrong-root-type", "missing-required-fields", "wrong-user-type"],
)
async def test_issue_tool_rejects_malformed_response(
    github_client,
    payload,
):
    url = "https://api.github.com/repos/acme/payments/issues/123"
    github_client.get.return_value = httpx.Response(
        200,
        json=payload,
        request=httpx.Request("GET", url),
    )

    result = await GitHubIssueTool().execute(
        ToolRequest(
            capability="github.get_issue",
            arguments={
                "owner": "acme",
                "repo": "payments",
                "issue_number": 123,
            },
        )
    )

    assert result.success is False
    assert result.error == "GitHub returned an invalid issue response"
