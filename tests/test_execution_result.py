from agentic_rag.models.execution_result import (
    ExecutionResult,
    ExecutionResults,
    ExecutionStatus,
    ToolCalled,
    ToolError,
)


def test_successful_execution_result():
    result = ExecutionResult(
        step_id="step-1",
        sub_query_id="sq-1",
        status=ExecutionStatus.SUCCESS,
        tool_called=ToolCalled(
            tool_id="github-search",
            tool_name="GitHub Search",
        ),
        tool_response=[
            {"repository": "agentic-rag", "status": "active"},
        ],
    )

    assert result.step_id == "step-1"
    assert result.status == ExecutionStatus.SUCCESS
    assert result.tool_response is not None


def test_failed_execution_result():
    result = ExecutionResult(
        step_id="step-2",
        sub_query_id="sq-2",
        status=ExecutionStatus.FAILED,
        tool_called=ToolCalled(
            tool_id="github-search",
            tool_name="GitHub Search",
        ),
        tool_error=ToolError(
            error_id="ERR-001",
            error_title="Tool execution failed",
            error_msg="GitHub API request failed",
        ),
    )

    assert result.status == ExecutionStatus.FAILED
    assert result.tool_error is not None


def test_execution_results():
    results = ExecutionResults(
        execution_results=[
            ExecutionResult(
                step_id="step-1",
                sub_query_id="sq-1",
                status=ExecutionStatus.SUCCESS,
            )
        ]
    )

    assert len(results.execution_results) == 1
