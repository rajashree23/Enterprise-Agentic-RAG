from agentic_rag.models.decomposition import QueryDecomposition, SubQuery
from agentic_rag.models.query import QueryInput


class DeterministicQueryDecomposer:
    def decompose(self, query_input: QueryInput) -> QueryDecomposition:
        return QueryDecomposition(
            sub_queries=[
                SubQuery(
                    sub_query_id="sq-1",
                    sub_query=query_input.query,
                )
            ]
        )
