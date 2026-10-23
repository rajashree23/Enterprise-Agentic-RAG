import pytest

from agentic_rag.execution.tool_operation import ToolExecutionOperation
from agentic_rag.models.capability import CapabilityDefinition
from agentic_rag.models.execution_plan import ExecutionStep
from agentic_rag.models.execution_result import ExecutionStatus
from agentic_rag.tools.github import GitHubSearchTool
from agentic_rag.tools.registry import CapabilityRegistry


@pytest.mark.asyncio
async def test_real_github_tool_through_execution_operation():
    registry = CapabilityRegistry()

    registry.register(
        CapabilityDefinition(
            name="github.search",
            description="Search GitHub issues",
            arguments={"query": "string"},
        ),
        GitHubSearchTool(),
    )

    operation = ToolExecutionOperation(registry)

    step = ExecutionStep(
        step_id="step-1",
        sub_query_id="sq-1",
        action="Find open FastAPI issues",
        capability="github.search",
        arguments={"query": "repo:fastapi/fastapi is:issue is:open"},
        depends_on=[],
    )

    result = await operation.execute(step)

    assert result.status == ExecutionStatus.SUCCESS
    assert result.tool_called.tool_name == "github.search"
    assert isinstance(result.tool_response, list)
    assert len(result.tool_response) > 0

    first_issue = result.tool_response[0]

    assert "title" in first_issue
    assert "state" in first_issue
    assert "url" in first_issue
