import httpx
from pydantic import ValidationError

from agentic_rag.models.github import (
    GitHubIssueArguments,
    GitHubIssueRecord,
)
from agentic_rag.models.tool import ToolRequest, ToolResult


class GitHubIssueTool:
    async def execute(self, request: ToolRequest) -> ToolResult:
        if request.capability != "github.get_issue":
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
            f"/{arguments.repo}/issues/{arguments.issue_number}"
        )

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    url,
                    headers={
                        "Accept": "application/vnd.github+json",
                        "X-GitHub-Api-Version": "2022-11-28",
                    },
                )
                response.raise_for_status()

                payload = response.json()

                if not isinstance(payload, dict):
                    raise TypeError("Expected an issue object")

                user = payload.get("user")

                if user is not None and not isinstance(user, dict):
                    raise ValueError("Expected a user object or null")

                record = GitHubIssueRecord(
                    id=payload["id"],
                    repository=f"{arguments.owner}/{arguments.repo}",
                    number=payload["number"],
                    record_type=(
                        "pull_request" if "pull_request" in payload else "issue"
                    ),
                    title=payload["title"],
                    body=payload.get("body"),
                    state=payload["state"],
                    url=payload["html_url"],
                    author=user.get("login") if user else None,
                    created_at=payload["created_at"],
                    updated_at=payload["updated_at"],
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
                error="GitHub returned an invalid issue response",
            )

        return ToolResult(
            capability=request.capability,
            success=True,
            data={"items": [record.model_dump(mode="json")]},
        )
