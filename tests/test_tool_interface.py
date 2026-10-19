from agentic_rag.models.tool import ToolRequest, ToolResult
from agentic_rag.tools.interface import Tool


class FakeTool:
    async def execute(self, request: ToolRequest) -> ToolResult:
        return ToolResult(
            capability=request.capability,
            success=True,
            data={"message": "Tool executed"},
        )


def test_fake_tool_satisfies_tool_protocol():
    tool = FakeTool()

    assert isinstance(tool, Tool)
