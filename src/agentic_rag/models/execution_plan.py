from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class LLMExecutionStep(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sub_query_id: str
    action: str
    capability: str
    arguments: dict[str, Any]
    depends_on_sub_query_ids: list[str]


class LLMExecutionPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    execution_steps: list[LLMExecutionStep]


class ExecutionStep(BaseModel):
    step_id: str
    sub_query_id: str
    action: str
    capability: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    depends_on: list[str]


class ExecutionPlan(BaseModel):
    execution_steps: list[ExecutionStep]
