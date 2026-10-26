from unittest.mock import AsyncMock, patch

import httpx
import pytest

from agentic_rag.models.tool import ToolRequest
from agentic_rag.tools.github.search import GitHubSearchTool


@pytest.mark.asyncio
async def test_github_search_handles_http_error():
    request = ToolRequest(
        capability="github.search",
        arguments={"query": "repo:fastapi/fastapi is:issue"},
    )

    http_request = httpx.Request(
        "GET",
        "https://api.github.com/search/issues",
    )
    http_response = httpx.Response(
        status_code=403,
        request=http_request,
    )

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = http_response

        result = await GitHubSearchTool().execute(request)

    assert result.success is False
    assert result.error == "GitHub API returned HTTP 403"


@pytest.mark.asyncio
async def test_github_search_handles_network_error():
    request = ToolRequest(
        capability="github.search",
        arguments={"query": "repo:fastapi/fastapi is:issue"},
    )

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.side_effect = httpx.ConnectError("Connection failed")

        result = await GitHubSearchTool().execute(request)

    assert result.success is False
    assert result.error == "GitHub request failed: ConnectError"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "arguments",
    [
        {},
        {"query": ""},
        {"query": "   "},
        {"query": 123},
        {"query": "bug", "unexpected": True},
    ],
    ids=["missing", "empty", "whitespace", "wrong-type", "extra-field"],
)
async def test_search_rejects_invalid_arguments(arguments):
    request = ToolRequest(
        capability="github.search",
        arguments=arguments,
    )

    with patch("agentic_rag.tools.github.search.httpx.AsyncClient") as client_factory:
        result = await GitHubSearchTool().execute(request)

    assert result.success is False
    assert result.error == "Invalid GitHub search arguments"
    client_factory.assert_not_called()


@pytest.mark.asyncio
async def test_search_preserves_records_and_metadata():
    url = "https://api.github.com/search/issues"
    payload = {
        "total_count": 18,
        "incomplete_results": False,
        "items": [
            {
                "id": 9001,
                "repository_url": ("https://api.github.com/repos/acme/payments"),
                "number": 123,
                "title": "Release payment retry feature",
                "body": "Waiting for migration approval.",
                "state": "open",
                "html_url": ("https://github.com/acme/payments/issues/123"),
                "user": {"login": "developer-a"},
                "created_at": "2026-10-20T10:00:00Z",
                "updated_at": "2026-10-24T10:00:00Z",
            }
        ],
    }

    request = ToolRequest(
        capability="github.search",
        arguments={"query": "repo:acme/payments migration"},
    )

    client = AsyncMock()
    client.get.return_value = httpx.Response(
        200,
        json=payload,
        request=httpx.Request("GET", url),
    )

    with patch("agentic_rag.tools.github.search.httpx.AsyncClient") as factory:
        factory.return_value.__aenter__.return_value = client

        result = await GitHubSearchTool().execute(request)

    assert result.success is True
    assert result.data["total_count"] == 18
    assert result.data["incomplete_results"] is False
    assert len(result.data["items"]) == 1

    record = result.data["items"][0]

    assert record["id"] == 9001
    assert record["repository"] == "acme/payments"
    assert record["number"] == 123
    assert record["record_type"] == "issue"
    assert record["body"] == "Waiting for migration approval."
    assert record["author"] == "developer-a"
    assert record["url"] == payload["items"][0]["html_url"]
    assert record["created_at"] == "2026-10-20T10:00:00Z"

    assert client.get.call_args.kwargs["params"] == {
        "q": "repo:acme/payments migration",
        "per_page": 5,
    }


@pytest.mark.asyncio
async def test_search_accepts_empty_results():
    url = "https://api.github.com/search/issues"
    client = AsyncMock()
    client.get.return_value = httpx.Response(
        200,
        json={
            "total_count": 0,
            "incomplete_results": False,
            "items": [],
        },
        request=httpx.Request("GET", url),
    )

    with patch("agentic_rag.tools.github.search.httpx.AsyncClient") as factory:
        factory.return_value.__aenter__.return_value = client

        result = await GitHubSearchTool().execute(
            ToolRequest(
                capability="github.search",
                arguments={"query": "repo:acme/payments migration"},
            )
        )

    assert result.success is True
    assert result.data == {
        "total_count": 0,
        "incomplete_results": False,
        "items": [],
    }


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload",
    [
        [],
        {},
        {
            "total_count": 1,
            "incomplete_results": False,
            "items": {},
        },
        {
            "total_count": -1,
            "incomplete_results": False,
            "items": [],
        },
        {
            "total_count": 1,
            "incomplete_results": False,
            "items": [{}],
        },
    ],
    ids=[
        "wrong-root-type",
        "missing-fields",
        "items-not-list",
        "negative-count",
        "malformed-record",
    ],
)
async def test_search_rejects_malformed_response(payload):
    url = "https://api.github.com/search/issues"
    client = AsyncMock()
    client.get.return_value = httpx.Response(
        200,
        json=payload,
        request=httpx.Request("GET", url),
    )

    with patch("agentic_rag.tools.github.search.httpx.AsyncClient") as factory:
        factory.return_value.__aenter__.return_value = client

        result = await GitHubSearchTool().execute(
            ToolRequest(
                capability="github.search",
                arguments={"query": "repo:acme/payments migration"},
            )
        )

    assert result.success is False
    assert result.error == "GitHub returned an invalid search response"
    assert result.data == {}
