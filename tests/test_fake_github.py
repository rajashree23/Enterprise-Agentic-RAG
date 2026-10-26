import pytest

from agentic_rag.models.capability import CapabilityDefinition
from agentic_rag.models.tool import ToolRequest
from agentic_rag.tools.github.fake_github import FakeGitHubSearchTool
from agentic_rag.tools.registry import CapabilityRegistry


@pytest.mark.asyncio
async def test_github_search_executes_through_registry():
    registry = CapabilityRegistry()
    github_tool = FakeGitHubSearchTool()

    registry.register(
        CapabilityDefinition(
            name="github.search",
            description="Search GitHub issues and pull requests.",
            arguments={"query": "string"},
        ),
        github_tool,
    )

    tool = registry.get("github.search")

    result = await tool.execute(
        ToolRequest(
            capability="github.search",
            arguments={"query": "Project X"},
        )
    )

    assert result.success is True
    assert result.capability == "github.search"
    assert result.data["items"][0]["state"] == "open"


@pytest.mark.asyncio
async def test_github_search_rejects_empty_query():
    tool = FakeGitHubSearchTool()

    result = await tool.execute(
        ToolRequest(
            capability="github.search",
            arguments={"query": "  "},
        )
    )

    assert result.success is False
    assert result.error == "A non-empty query is required"
