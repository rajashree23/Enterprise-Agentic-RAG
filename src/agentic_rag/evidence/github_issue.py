from uuid import uuid4

from agentic_rag.models.evidence import Evidence, EvidenceSource
from agentic_rag.models.execution_result import (
    ExecutionResult,
    ExecutionStatus,
)
from agentic_rag.models.github import GitHubIssueRecord


class GitHubIssueNormalizer:
    def __init__(self, capability: str = "github.get_issue"):
        self.capability = capability

    def normalize(self, result: ExecutionResult) -> list[Evidence]:
        if result.status != ExecutionStatus.SUCCESS:
            return []

        if result.tool_called is None:
            raise ValueError("Successful result must identify its tool")

        if result.tool_called.tool_id != self.capability:
            raise ValueError("Unsupported capability for issue normalization")

        if result.tool_response is None:
            raise ValueError("Successful issue result must contain tool_response")

        records = [
            GitHubIssueRecord.model_validate(item) for item in result.tool_response
        ]

        evidence_items = []

        for record in records:
            evidence = Evidence(
                evidence_id=str(uuid4()),
                step_id=result.step_id,
                sub_query_id=result.sub_query_id,
                tool_called=result.tool_called,
                source=EvidenceSource(
                    system="github",
                    record_type=record.record_type,
                    record_id=str(record.id),
                    url=record.url,
                    title=record.title,
                    author=record.author,
                    created_at=record.created_at,
                    updated_at=record.updated_at,
                ),
                tool_response=[record.model_dump(mode="json")],
                content=self._build_content(record),
            )
            evidence_items.append(evidence)

        return evidence_items

    @staticmethod
    def _build_content(record: GitHubIssueRecord) -> str:
        parts = [
            f"Repository: {record.repository}",
            f"Number: {record.number}",
            f"Type: {record.record_type}",
            f"Title: {record.title}",
            f"State: {record.state}",
        ]

        if record.body:
            parts.append(f"Description: {record.body}")

        return "\n".join(parts)
