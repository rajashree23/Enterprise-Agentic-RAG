import httpx
from pydantic import ValidationError

from agentic_rag.models.github import (
    GitHubCommentRecord,
    GitHubIssueArguments,
)
from agentic_rag.models.tool import ToolRequest, ToolResult


class GitHubIssueCommentsTool:
    def __init__(self, max_pages: int = 3, per_page: int = 100):
        if max_pages < 1:
            raise ValueError("max_pages must be positive")

        if not 1 <= per_page <= 100:
            raise ValueError("per_page must be between 1 and 100")

        self.max_pages = max_pages
        self.per_page = per_page

    async def execute(self, request: ToolRequest) -> ToolResult:
        if request.capability != "github.list_issue_comments":
            return ToolResult(
                capability=request.capability,
                success=False,
                error="Unsupported capability",
            )

        try:
            arguments = GitHubIssueArguments.model_validate(request.arguments)
        except ValidationError:
            return ToolResult(
                capability=request.capability,
                success=False,
                error="Invalid GitHub issue arguments",
            )

        url = (
            f"https://api.github.com/repos/{arguments.owner}"
            f"/{arguments.repo}/issues/{arguments.issue_number}/comments"
        )

        records: list[GitHubCommentRecord] = []
        has_more = False
        pages_fetched = 0

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                for page in range(1, self.max_pages + 1):
                    response = await client.get(
                        url,
                        params={
                            "per_page": self.per_page,
                            "page": page,
                        },
                        headers={
                            "Accept": "application/vnd.github+json",
                            "X-GitHub-Api-Version": "2022-11-28",
                        },
                    )
                    response.raise_for_status()
                    payload = response.json()

                    if not isinstance(payload, list):
                        raise TypeError("Expected a comment list")

                    page_records = [
                        self._to_record(item, arguments) for item in payload
                    ]
                    records.extend(page_records)
                    pages_fetched += 1

                    has_more = "next" in response.links

                    if not has_more:
                        break

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
                error="GitHub returned an invalid comments response",
            )

        return ToolResult(
            capability=request.capability,
            success=True,
            data={
                "items": [record.model_dump(mode="json") for record in records],
                "has_more": has_more,
                "pages_fetched": pages_fetched,
                "per_page": self.per_page,
            },
        )

    @staticmethod
    def _to_record(
        item: dict,
        arguments: GitHubIssueArguments,
    ) -> GitHubCommentRecord:
        if not isinstance(item, dict):
            raise TypeError("Expected a comment object")

        user = item.get("user")

        if user is not None and not isinstance(user, dict):
            raise TypeError("Expected a user object or null")

        return GitHubCommentRecord(
            id=item["id"],
            repository=f"{arguments.owner}/{arguments.repo}",
            issue_number=arguments.issue_number,
            body=item.get("body"),
            url=item["html_url"],
            author=user.get("login") if user else None,
            created_at=item["created_at"],
            updated_at=item["updated_at"],
        )
