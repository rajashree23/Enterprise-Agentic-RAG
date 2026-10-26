from datetime import datetime

from pydantic import BaseModel

from agentic_rag.models.execution_result import ToolCalled


class EvidenceSource(BaseModel):
    system: str
    record_type: str
    record_id: str
    url: str
    title: str | None = None
    author: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class Evidence(BaseModel):
    source: EvidenceSource
    evidence_id: str
    step_id: str
    sub_query_id: str
    tool_called: ToolCalled
    tool_response: list[dict] | None = None
    content: str
