from pydantic import BaseModel


class SubQuery(BaseModel):
    sub_query_id: str
    sub_query: str


class QueryDecomposition(BaseModel):
    sub_queries: list[SubQuery]
