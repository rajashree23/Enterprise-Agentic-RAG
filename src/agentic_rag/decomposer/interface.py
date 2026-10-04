from typing import Protocol

from agentic_rag.models.decomposition import QueryDecomposition
from agentic_rag.models.query import QueryInput


class QueryDecomposer(Protocol):
    def decompose(
        self,
        query_input: QueryInput,
    ) -> QueryDecomposition: ...
