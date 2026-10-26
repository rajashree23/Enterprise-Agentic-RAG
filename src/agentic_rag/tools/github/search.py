import httpx
from pydantic import ValidationError

from agentic_rag.models.github import (
    GitHubIssueRecord,
    GitHubSearchArguments,
    GitHubSearchResults,
)
from agentic_rag.models.tool import ToolRequest, ToolResult


class GitHubSearchTool:
    async def execute(self, request: ToolRequest) -> ToolResult:
        if request.capability != "github.search":
            return ToolResult(
                capability=request.capability,
                success=False,
                error="Unsupported capability",
            )

        try:
            arguments = GitHubSearchArguments.model_validate(request.arguments)
        except ValidationError:
            return ToolResult(
                capability=request.capability,
                success=False,
                error="Invalid GitHub search arguments",
            )

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    "https://api.github.com/search/issues",
                    params={"q": arguments.query, "per_page": 5},
                    headers={
                        "Accept": "application/vnd.github+json",
                        "X-GitHub-Api-Version": "2022-11-28",
                    },
                )
                response.raise_for_status()
                payload = response.json()

            if not isinstance(payload, dict):
                raise TypeError("Expected a search response object")

            raw_items = payload["items"]

            if not isinstance(raw_items, list):
                raise TypeError("Expected a list of search results")

            records = [self._to_record(item) for item in raw_items]

            search_results = GitHubSearchResults(
                total_count=payload["total_count"],
                incomplete_results=payload["incomplete_results"],
                items=records,
            )

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

        except (ValueError, KeyError, TypeError):
            return ToolResult(
                capability=request.capability,
                success=False,
                error="GitHub returned an invalid search response",
            )

        return ToolResult(
            capability=request.capability,
            success=True,
            data=search_results.model_dump(mode="json"),
        )

    @staticmethod
    def _to_record(item: dict) -> GitHubIssueRecord:
        if not isinstance(item, dict):
            raise TypeError("Expected a search result object")

        repository_url = item["repository_url"]
        prefix = "https://api.github.com/repos/"

        if not isinstance(repository_url, str):
            raise TypeError("Expected a repository URL string")

        if not repository_url.startswith(prefix):
            raise ValueError("Unexpected repository URL")

        repository = repository_url.removeprefix(prefix)
        repository_parts = repository.split("/")

        if len(repository_parts) != 2 or not all(repository_parts):
            raise ValueError("Expected an owner/repository identifier")

        user = item.get("user")

        if user is not None and not isinstance(user, dict):
            raise TypeError("Expected a user object or null")

        return GitHubIssueRecord(
            id=item["id"],
            repository=repository,
            number=item["number"],
            record_type=("pull_request" if "pull_request" in item else "issue"),
            title=item["title"],
            body=item.get("body"),
            state=item["state"],
            url=item["html_url"],
            author=user.get("login") if user else None,
            created_at=item["created_at"],
            updated_at=item["updated_at"],
        )
