from pydantic import BaseModel

from agentic_rag.models.execution_result import ToolCalled


class Evidence(BaseModel):
    evidence_id: str
    step_id: str
    sub_query_id: str
    tool_called: ToolCalled
    tool_response: list[dict] | None = None
    content: str


class EvidenceCollection(BaseModel):
    evidence: list[Evidence]
    is_sufficient: bool
