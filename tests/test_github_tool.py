from unittest.mock import AsyncMock, patch

import httpx
import pytest

from agentic_rag.models.tool import ToolRequest
from agentic_rag.tools.github import GitHubSearchTool


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
