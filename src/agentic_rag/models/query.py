from pydantic import BaseModel


class QueryInput(BaseModel):
    conversation_id: str | None = None
    query: str
