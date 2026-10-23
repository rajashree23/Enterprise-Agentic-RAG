import pytest

from agentic_rag.execution.tool_operation import ToolExecutionOperation
from agentic_rag.models.capability import CapabilityDefinition
from agentic_rag.models.execution_plan import ExecutionStep
from agentic_rag.models.execution_result import ExecutionStatus
from agentic_rag.models.tool import ToolRequest, ToolResult
from agentic_rag.tools.registry import CapabilityRegistry


class FakeGitHubTool:
    async def execute(self, request: ToolRequest) -> ToolResult:
        return ToolResult(
            capability=request.capability,
            success=True,
            data={
                "items": [
                    {
                        "title": "Example issue",
                        "state": "open",
                    }
                ]
            },
        )


class FakeGitHubFailureTool:
    async def execute(self, request: ToolRequest) -> ToolResult:
        return ToolResult(
            capability=request.capability,
            success=False,
            error="GitHub API returned HTTP 403",
        )


class FailingGitHubTool:
    async def execute(self, request: ToolRequest) -> ToolResult:
        return ToolResult(
            capability=request.capability,
            success=False,
            error="GitHub API unavailable",
        )


def create_step() -> ExecutionStep:
    return ExecutionStep(
        step_id="step-1",
        sub_query_id="sq-1",
        action="Search issues about Project X",
        capability="github.search",
        arguments={"query": "Search issues about Project X"},
        depends_on=[],
    )


@pytest.mark.asyncio
async def test_tool_operation_returns_success_and_response():
    registry = CapabilityRegistry()
    registry.register(
        CapabilityDefinition(
            name="github.search",
            description="Search GitHub issues and pull requests.",
            arguments={"query": "string"},
        ),
        FakeGitHubTool(),
    )

    operation = ToolExecutionOperation(registry)

    result = await operation.execute(create_step())

    assert result.status == ExecutionStatus.SUCCESS
    assert result.step_id == "step-1"
    assert result.sub_query_id == "sq-1"
    assert result.tool_called is not None
    assert result.tool_called.tool_id == "github.search"
    assert result.tool_response == [{"title": "Example issue", "state": "open"}]
    assert result.tool_error is None


@pytest.mark.asyncio
async def test_tool_operation_returns_failure_when_tool_fails():
    registry = CapabilityRegistry()
    registry.register(
        CapabilityDefinition(
            name="github.search",
            description="Search GitHub issues and pull requests.",
            arguments={"query": "string"},
        ),
        FailingGitHubTool(),
    )

    operation = ToolExecutionOperation(registry)

    result = await operation.execute(create_step())

    assert result.status == ExecutionStatus.FAILED
    assert result.tool_called is not None
    assert result.tool_error is not None
    assert result.tool_error.error_msg == "GitHub API unavailable"


@pytest.mark.asyncio
async def test_tool_operation_fails_for_unknown_capability():
    registry = CapabilityRegistry()
    operation = ToolExecutionOperation(registry)

    result = await operation.execute(create_step())

    assert result.status == ExecutionStatus.FAILED
    assert result.tool_error is not None
    assert result.tool_error.error_id == "tool_execution_error"


@pytest.mark.asyncio
async def test_tool_operation_passes_query_to_tool():
    class RecordingGitHubTool:
        def __init__(self):
            self.received_request = None

        async def execute(self, request: ToolRequest) -> ToolResult:
            self.received_request = request

            return ToolResult(
                capability=request.capability,
                success=True,
                data={"items": []},
            )

    registry = CapabilityRegistry()
    tool = RecordingGitHubTool()
    registry.register(
        CapabilityDefinition(
            name="github.search",
            description="Search GitHub issues and pull requests.",
            arguments={"query": "string"},
        ),
        tool,
    )

    operation = ToolExecutionOperation(registry)

    step = create_step()
    await operation.execute(step)

    assert tool.received_request is not None
    assert tool.received_request.capability == "github.search"
    assert tool.received_request.arguments == {"query": "Search issues about Project X"}


@pytest.mark.asyncio
async def test_tool_operation_handles_failed_tool_result():
    registry = CapabilityRegistry()

    registry.register(
        CapabilityDefinition(
            name="github.search",
            description="Search GitHub issues",
            arguments={"query": "string"},
        ),
        FakeGitHubFailureTool(),
    )

    operation = ToolExecutionOperation(registry)

    step = ExecutionStep(
        step_id="step-1",
        sub_query_id="sq-1",
        action="Search GitHub issues",
        capability="github.search",
        arguments={"query": "Project X"},
        depends_on=[],
    )

    result = await operation.execute(step)

    assert result.status == ExecutionStatus.FAILED
    assert result.tool_error is not None
    assert result.tool_error.error_id == "tool_execution_failed"
    assert result.tool_error.error_msg == "GitHub API returned HTTP 403"
