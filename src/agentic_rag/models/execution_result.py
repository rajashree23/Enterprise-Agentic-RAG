from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ExecutionStatus(str, Enum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


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
    tool_metadata: dict[str, Any] = Field(default_factory=dict)


class ExecutionResults(BaseModel):
    execution_results: list[ExecutionResult]
