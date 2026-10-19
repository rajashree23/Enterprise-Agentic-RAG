from typing import Protocol, runtime_checkable

from agentic_rag.models.tool import ToolRequest, ToolResult


@runtime_checkable
class Tool(Protocol):
    async def execute(self, request: ToolRequest) -> ToolResult: ...
