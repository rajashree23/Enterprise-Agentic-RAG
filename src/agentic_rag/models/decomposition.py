from pydantic import BaseModel


class SubQuery(BaseModel):
    sub_query_id: str
    sub_query: str


class QueryDecomposition(BaseModel):
    sub_queries: list[SubQuery]


class LLMSubQuery(BaseModel):
    sub_query: str


class LLMQueryDecomposition(BaseModel):
    sub_queries: list[LLMSubQuery]
