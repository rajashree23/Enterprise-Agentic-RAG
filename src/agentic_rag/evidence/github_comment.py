from uuid import uuid4

from agentic_rag.models.evidence import Evidence, EvidenceSource
from agentic_rag.models.execution_result import (
    ExecutionResult,
    ExecutionStatus,
)
from agentic_rag.models.github import GitHubCommentRecord


class GitHubCommentNormalizer:
    def normalize(self, result: ExecutionResult) -> list[Evidence]:
        if result.status != ExecutionStatus.SUCCESS:
            return []

        if result.tool_called is None:
            raise ValueError("Successful result must identify its tool")

        if result.tool_called.tool_id != "github.list_issue_comments":
            raise ValueError("Unsupported capability for comment normalization")

        if result.tool_response is None:
            raise ValueError("Successful comment result must contain tool_response")

        records = [
            GitHubCommentRecord.model_validate(item) for item in result.tool_response
        ]

        evidence_items = []

        for record in records:
            evidence_items.append(
                Evidence(
                    evidence_id=str(uuid4()),
                    step_id=result.step_id,
                    sub_query_id=result.sub_query_id,
                    tool_called=result.tool_called,
                    source=EvidenceSource(
                        system="github",
                        record_type=record.record_type,
                        record_id=str(record.id),
                        url=record.url,
                        author=record.author,
                        created_at=record.created_at,
                        updated_at=record.updated_at,
                    ),
                    tool_response=[record.model_dump(mode="json")],
                    content=self._build_content(record),
                )
            )

        return evidence_items

    @staticmethod
    def _build_content(record: GitHubCommentRecord) -> str:
        parts = [
            f"Repository: {record.repository}",
            f"Issue or PR number: {record.issue_number}",
            f"Comment ID: {record.id}",
        ]

        if record.author:
            parts.append(f"Author: {record.author}")

        parts.append(f"Created at: {record.created_at.isoformat()}")
        parts.append(f"Updated at: {record.updated_at.isoformat()}")

        if record.body:
            parts.append(f"Comment: {record.body}")

        return "\n".join(parts)
