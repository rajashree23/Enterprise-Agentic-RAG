import pytest
from pydantic import ValidationError

from agentic_rag.models.tool import ToolRequest, ToolResult


def test_tool_request_accepts_valid_request():
    request = ToolRequest(
        capability="github.search",
        arguments={"query": "project status"},
    )

    assert request.capability == "github.search"
    assert request.arguments["query"] == "project status"


def test_tool_request_rejects_extra_fields():
    with pytest.raises(ValidationError):
        ToolRequest(
            capability="github.search",
            arguments={},
            unexpected="value",
        )


def test_tool_result_accepts_success():
    result = ToolResult(
        capability="github.search",
        success=True,
        data={"items": []},
    )

    assert result.success is True
    assert result.error is None


def test_tool_result_accepts_failure():
    result = ToolResult(
        capability="github.search",
        success=False,
        error="GitHub API unavailable",
    )

    assert result.success is False
    assert result.error == "GitHub API unavailable"
