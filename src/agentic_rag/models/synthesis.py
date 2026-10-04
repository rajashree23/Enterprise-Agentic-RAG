from pydantic import BaseModel


class Citation(BaseModel):
    evidence_id: str


class Synthesis(BaseModel):
    response: str
    citations: list[Citation]
