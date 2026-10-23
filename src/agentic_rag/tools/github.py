import httpx

from agentic_rag.models.tool import ToolRequest, ToolResult


class GitHubSearchTool:
    async def execute(self, request: ToolRequest) -> ToolResult:
        query = request.arguments["query"]

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    "https://api.github.com/search/issues",
                    params={"q": query, "per_page": 5},
                    headers={
                        "Accept": "application/vnd.github+json",
                        "X-GitHub-Api-Version": "2022-11-28",
                    },
                )

                response.raise_for_status()
                payload = response.json()

        except httpx.HTTPStatusError as exc:
            return ToolResult(
                capability=request.capability,
                success=False,
                error=(f"GitHub API returned HTTP {exc.response.status_code}"),
            )

        except httpx.RequestError as exc:
            return ToolResult(
                capability=request.capability,
                success=False,
                error=f"GitHub request failed: {type(exc).__name__}",
            )

        items = [
            {
                "title": item["title"],
                "state": item["state"],
                "url": item["html_url"],
            }
            for item in payload["items"]
        ]

        return ToolResult(
            capability=request.capability,
            success=True,
            data={"items": items},
        )
