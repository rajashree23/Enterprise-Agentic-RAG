from unittest.mock import AsyncMock, patch
from uuid import UUID, uuid4

import httpx
import pytest

from agentic_rag.composition import create_normalizers, create_registry
from agentic_rag.execution.tool_operation import ToolExecutionOperation
from agentic_rag.models.execution_plan import ExecutionStep
from agentic_rag.models.execution_result import ExecutionStatus
from agentic_rag.models.tool import ToolRequest
from agentic_rag.tools.github.comments import GitHubIssueCommentsTool

COMMENTS_URL = "https://api.github.com/repos/acme/payments/issues/123/comments"


def make_comment(comment_id: int) -> dict:
    return {
        "id": comment_id,
        "body": f"Update from comment {comment_id}",
        "html_url": (
            f"https://github.com/acme/payments/issues/123#issuecomment-{comment_id}"
        ),
        "user": {"login": "developer-a"},
        "created_at": "2026-10-20T10:00:00Z",
        "updated_at": "2026-10-24T10:00:00Z",
    }


def make_response(
    comment_ids: list[int],
    has_next: bool,
    next_page: int,
) -> httpx.Response:
    headers = {}

    if has_next:
        headers["Link"] = f'<{COMMENTS_URL}?page={next_page}>; rel="next"'

    return httpx.Response(
        200,
        json=[make_comment(comment_id) for comment_id in comment_ids],
        headers=headers,
        request=httpx.Request("GET", COMMENTS_URL),
    )


@pytest.fixture
def comment_request():
    return ToolRequest(
        capability="github.list_issue_comments",
        arguments={
            "owner": "acme",
            "repo": "payments",
            "issue_number": 123,
        },
    )


@pytest.fixture
def github_client():
    client = AsyncMock()

    with patch("agentic_rag.tools.github.comments.httpx.AsyncClient") as factory:
        factory.return_value.__aenter__.return_value = client
        yield client


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("pages", "max_pages", "expected_ids", "expected_has_more"),
    [
        ([([7001], False)], 3, [7001], False),
        ([([7001], True), ([7002], False)], 3, [7001, 7002], False),
        ([([7001], True)], 1, [7001], True),
        ([([], False)], 3, [], False),
    ],
    ids=["one-page", "two-pages", "page-limit", "empty-discussion"],
)
async def test_comment_pagination(
    github_client,
    comment_request,
    pages,
    max_pages,
    expected_ids,
    expected_has_more,
):
    github_client.get.side_effect = [
        make_response(ids, has_next, next_page=index + 2)
        for index, (ids, has_next) in enumerate(pages)
    ]

    tool = GitHubIssueCommentsTool(max_pages=max_pages)
    result = await tool.execute(comment_request)

    assert result.success is True
    assert result.error is None
    assert [item["id"] for item in result.data["items"]] == expected_ids
    assert result.data["has_more"] is expected_has_more
    assert result.data["pages_fetched"] == len(pages)
    assert result.data["per_page"] == 100

    assert github_client.get.await_count == len(pages)

    for page_number, call in enumerate(
        github_client.get.call_args_list,
        start=1,
    ):
        assert call.args[0] == COMMENTS_URL
        assert call.kwargs["params"] == {
            "per_page": 100,
            "page": page_number,
        }

    for item in result.data["items"]:
        assert item["repository"] == "acme/payments"
        assert item["issue_number"] == 123
        assert item["record_type"] == "issue_comment"
        assert item["url"].endswith(f"#issuecomment-{item['id']}")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status_code", "payload", "expected_error"),
    [
        (404, {}, "GitHub API returned HTTP 404"),
        (
            200,
            {},
            "GitHub returned an invalid comments response",
        ),
        (
            200,
            [{}],
            "GitHub returned an invalid comments response",
        ),
        (
            200,
            [make_comment(7001) | {"user": "invalid"}],
            "GitHub returned an invalid comments response",
        ),
    ],
    ids=["not-found", "wrong-root-type", "missing-fields", "invalid-user"],
)
async def test_comments_reject_failed_or_invalid_response(
    github_client,
    comment_request,
    status_code,
    payload,
    expected_error,
):
    github_client.get.return_value = httpx.Response(
        status_code,
        json=payload,
        request=httpx.Request("GET", COMMENTS_URL),
    )

    result = await GitHubIssueCommentsTool().execute(comment_request)

    assert result.success is False
    assert result.error == expected_error
    assert result.data == {}


@pytest.mark.asyncio
async def test_comments_handle_network_failure(
    github_client,
    comment_request,
):
    github_client.get.side_effect = httpx.ConnectError("Connection unavailable")

    result = await GitHubIssueCommentsTool().execute(comment_request)

    assert result.success is False
    assert result.error == "GitHub request failed: ConnectError"
    assert result.data == {}


@pytest.mark.asyncio
async def test_later_page_failure_does_not_return_partial_success(
    github_client,
    comment_request,
):
    github_client.get.side_effect = [
        make_response([7001], has_next=True, next_page=2),
        httpx.Response(
            403,
            request=httpx.Request("GET", COMMENTS_URL),
        ),
    ]

    result = await GitHubIssueCommentsTool().execute(comment_request)

    assert github_client.get.await_count == 2
    assert result.success is False
    assert result.error == "GitHub API returned HTTP 403"
    assert result.data == {}


@pytest.mark.asyncio
async def test_invalid_comment_arguments_make_no_http_request(
    github_client,
):
    request = ToolRequest(
        capability="github.list_issue_comments",
        arguments={
            "owner": "acme",
            "repo": "payments",
            "issue_number": "123",
        },
    )

    result = await GitHubIssueCommentsTool().execute(request)

    assert result.success is False
    assert result.error == "Invalid GitHub issue arguments"
    github_client.get.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "comment_ids",
    [[7001, 7002], []],
    ids=["two-comments", "no-comments"],
)
async def test_registered_comments_produce_evidence(
    github_client,
    comment_ids,
):
    github_client.get.return_value = make_response(
        comment_ids,
        has_next=False,
        next_page=2,
    )

    step = ExecutionStep(
        step_id=str(uuid4()),
        sub_query_id=str(uuid4()),
        action="Retrieve discussion comments",
        capability="github.list_issue_comments",
        arguments={
            "owner": "acme",
            "repo": "payments",
            "issue_number": 123,
        },
        depends_on=[],
    )

    operation = ToolExecutionOperation(create_registry())
    result = await operation.execute(step)

    assert result.status == ExecutionStatus.SUCCESS
    assert result.tool_metadata == {
        "has_more": False,
        "pages_fetched": 1,
        "per_page": 100,
    }

    normalizer = create_normalizers()["github.list_issue_comments"]
    evidence_items = normalizer.normalize(result)

    assert len(evidence_items) == len(comment_ids)
    assert len({item.evidence_id for item in evidence_items}) == len(comment_ids)

    for evidence, comment_id in zip(evidence_items, comment_ids):
        assert UUID(evidence.evidence_id).version == 4
        assert evidence.step_id == step.step_id
        assert evidence.sub_query_id == step.sub_query_id
        assert evidence.source.record_type == "issue_comment"
        assert evidence.source.record_id == str(comment_id)
        assert evidence.source.url == (
            f"https://github.com/acme/payments/issues/123#issuecomment-{comment_id}"
        )
        assert evidence.source.created_at.tzinfo is not None
        assert f"Update from comment {comment_id}" in evidence.content
        assert "Created at:" in evidence.content
        assert evidence.tool_response[0]["id"] == comment_id
