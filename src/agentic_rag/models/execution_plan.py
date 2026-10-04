from pydantic import BaseModel


class ExecutionStep(BaseModel):
    step_id: str
    sub_query_id: str
    action: str
    capability: str
    depends_on: list[str]


class ExecutionPlan(BaseModel):
    execution_steps: list[ExecutionStep]
