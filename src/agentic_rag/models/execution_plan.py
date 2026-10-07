from pydantic import BaseModel


class LLMExecutionStep(BaseModel):
    sub_query_id: str
    action: str
    capability: str
    depends_on_sub_query_ids: list[str]


class LLMExecutionPlan(BaseModel):
    execution_steps: list[LLMExecutionStep]


class ExecutionStep(BaseModel):
    step_id: str
    sub_query_id: str
    action: str
    capability: str
    depends_on: list[str]


class ExecutionPlan(BaseModel):
    execution_steps: list[ExecutionStep]
