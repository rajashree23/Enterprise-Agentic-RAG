from uuid import UUID, uuid4

import pytest

from agentic_rag.composition import create_normalizers
from agentic_rag.evidence.github_issue import GitHubIssueNormalizer
from agentic_rag.models.execution_result import (
    ExecutionResult,
    ExecutionStatus,
    ToolCalled,
)


@pytest.fixture
def issue_record():
    return {
        "id": 9001,
        "repository": "acme/payments",
        "number": 123,
        "record_type": "issue",
        "title": "Release payment retry feature",
        "body": "Waiting for migration approval.",
        "state": "open",
        "url": "https://github.com/acme/payments/issues/123",
        "author": "developer-a",
        "created_at": "2026-10-20T10:00:00Z",
        "updated_at": "2026-10-24T10:00:00Z",
    }


@pytest.fixture
def result_data(issue_record):
    return {
        "step_id": str(uuid4()),
        "sub_query_id": str(uuid4()),
        "status": ExecutionStatus.SUCCESS,
        "tool_called": ToolCalled(
            tool_id="github.get_issue",
            tool_name="github.get_issue",
        ),
        "tool_response": [issue_record],
    }


def test_normalizes_issue_with_provenance(result_data, issue_record):
    result = ExecutionResult(**result_data)

    items = GitHubIssueNormalizer().normalize(result)

    assert len(items) == 1
    evidence = items[0]

    assert UUID(evidence.evidence_id).version == 4
    assert evidence.step_id == result.step_id
    assert evidence.sub_query_id == result.sub_query_id
    assert evidence.tool_called == result.tool_called

    assert evidence.source.system == "github"
    assert evidence.source.record_type == "issue"
    assert evidence.source.record_id == str(issue_record["id"])
    assert evidence.source.url == issue_record["url"]
    assert evidence.source.author == issue_record["author"]
    assert evidence.source.created_at.tzinfo is not None

    assert evidence.tool_response[0]["body"] == issue_record["body"]
    assert "Title: Release payment retry feature" in evidence.content
    assert "State: open" in evidence.content
    assert "Description: Waiting for migration approval." in evidence.content


@pytest.mark.parametrize(
    "status",
    [ExecutionStatus.FAILED, ExecutionStatus.SKIPPED],
)
def test_unsuccessful_execution_produces_no_evidence(status):
    result = ExecutionResult(
        step_id=str(uuid4()),
        sub_query_id=str(uuid4()),
        status=status,
    )

    assert GitHubIssueNormalizer().normalize(result) == []


def test_empty_response_produces_no_evidence(result_data):
    result_data["tool_response"] = []
    result = ExecutionResult(**result_data)

    assert GitHubIssueNormalizer().normalize(result) == []


def test_missing_body_is_not_invented(result_data, issue_record):
    issue_record["body"] = None
    result = ExecutionResult(**result_data)

    evidence = GitHubIssueNormalizer().normalize(result)[0]

    assert "Description:" not in evidence.content
    assert evidence.tool_response[0]["body"] is None


@pytest.mark.parametrize(
    ("changes", "message"),
    [
        ({"tool_called": None}, "must identify its tool"),
        (
            {
                "tool_called": ToolCalled(
                    tool_id="github.search",
                    tool_name="github.search",
                )
            },
            "Unsupported capability",
        ),
        ({"tool_response": None}, "must contain tool_response"),
        ({"tool_response": [{}]}, None),
    ],
    ids=[
        "missing-tool",
        "unsupported-capability",
        "missing-response",
        "malformed-record",
    ],
)
def test_rejects_invalid_success_result(result_data, changes, message):
    result_data.update(changes)
    result = ExecutionResult(**result_data)

    with pytest.raises(ValueError, match=message):
        GitHubIssueNormalizer().normalize(result)


def test_repeated_normalization_creates_distinct_evidence_ids(result_data):
    result = ExecutionResult(**result_data)
    normalizer = GitHubIssueNormalizer()

    first = normalizer.normalize(result)[0]
    second = normalizer.normalize(result)[0]

    assert first.evidence_id != second.evidence_id
    assert first.source.record_id == second.source.record_id


def test_registered_search_normalizer_creates_evidence(result_data):
    result_data["tool_called"] = ToolCalled(
        tool_id="github.search",
        tool_name="github.search",
    )
    result_data["tool_metadata"] = {
        "total_count": 18,
        "incomplete_results": True,
    }
    result = ExecutionResult(**result_data)

    normalizer = create_normalizers()["github.search"]
    items = normalizer.normalize(result)

    assert len(items) == 1
    evidence = items[0]

    assert evidence.tool_called.tool_id == "github.search"
    assert evidence.source.record_id == "9001"
    assert evidence.source.url == ("https://github.com/acme/payments/issues/123")
    assert "Waiting for migration approval." in evidence.content

    assert result.tool_metadata == {
        "total_count": 18,
        "incomplete_results": True,
    }


def test_registered_search_normalizer_accepts_no_matches(result_data):
    result_data["tool_called"] = ToolCalled(
        tool_id="github.search",
        tool_name="github.search",
    )
    result_data["tool_response"] = []
    result = ExecutionResult(**result_data)

    normalizer = create_normalizers()["github.search"]

    assert normalizer.normalize(result) == []
