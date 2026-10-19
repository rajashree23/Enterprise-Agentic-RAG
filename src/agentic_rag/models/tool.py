from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ToolRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    capability: str = Field(min_length=1)
    arguments: dict[str, Any] = Field(default_factory=dict)


class ToolResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    capability: str = Field(min_length=1)
    success: bool
    data: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
