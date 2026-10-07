from pydantic import BaseModel


class LLMSubQuery(BaseModel):
    sub_query: str


class LLMQueryDecomposition(BaseModel):
    sub_queries: list[LLMSubQuery]


class SubQuery(BaseModel):
    sub_query_id: str
    sub_query: str


class QueryDecomposition(BaseModel):
    sub_queries: list[SubQuery]
