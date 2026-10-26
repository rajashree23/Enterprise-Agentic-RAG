from agentic_rag.models.tool import ToolRequest, ToolResult


class FakeGitHubSearchTool:
    async def execute(self, request: ToolRequest) -> ToolResult:
        if request.capability != "github.search":
            return ToolResult(
                capability=request.capability,
                success=False,
                error="Unsupported capability",
            )

        query = request.arguments.get("query")

        if not isinstance(query, str) or not query.strip():
            return ToolResult(
                capability="github.search",
                success=False,
                error="A non-empty query is required",
            )

        return ToolResult(
            capability="github.search",
            success=True,
            data={
                "items": [
                    {
                        "title": f"Example issue matching: {query}",
                        "state": "open",
                        "url": "https://github.com/example/repo/issues/1",
                    }
                ]
            },
        )
