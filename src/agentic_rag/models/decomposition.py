from pydantic import BaseModel, ConfigDict


class LLMSubQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sub_query: str


class LLMQueryDecomposition(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sub_queries: list[LLMSubQuery]


class SubQuery(BaseModel):
    sub_query_id: str
    sub_query: str


class QueryDecomposition(BaseModel):
    sub_queries: list[SubQuery]
