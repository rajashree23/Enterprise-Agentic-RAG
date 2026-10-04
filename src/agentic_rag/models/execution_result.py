from enum import Enum

from pydantic import BaseModel


class ExecutionStatus(str, Enum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class ToolCalled(BaseModel):
    tool_id: str
    tool_name: str


class ToolError(BaseModel):
    error_id: str
    error_title: str
    error_msg: str


class ExecutionResult(BaseModel):
    step_id: str
    sub_query_id: str
    status: ExecutionStatus
    tool_called: ToolCalled | None = None
    tool_response: list[dict] | None = None
    tool_error: ToolError | None = None


class ExecutionResults(BaseModel):
    execution_results: list[ExecutionResult]
