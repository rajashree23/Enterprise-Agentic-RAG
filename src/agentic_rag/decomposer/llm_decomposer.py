from agentic_rag.llm.interface import LLM
from agentic_rag.models.decomposition import (
    LLMQueryDecomposition,
    QueryDecomposition,
    SubQuery,
)
from agentic_rag.models.query import QueryInput


class LLMQueryDecomposer:
    def __init__(self, llm: LLM):
        self.llm = llm

    async def decompose(
        self,
        query_input: QueryInput,
    ) -> QueryDecomposition:
        prompt = f"""
You are a query decomposition system.

Break the user's query into smaller, independent sub-queries
that can be executed separately.

Return ONLY valid JSON in this exact format:

{{
  "sub_queries": [
    {{
      "sub_query": "..."
    }}
  ]
}}

User query:
{query_input.query}
"""

        response = await self.llm.generate(prompt)

        llm_decomposition = LLMQueryDecomposition.model_validate_json(response)

        sub_queries = [
            SubQuery(
                sub_query_id=f"sq-{index}",
                sub_query=sub_query.sub_query,
            )
            for index, sub_query in enumerate(
                llm_decomposition.sub_queries,
                start=1,
            )
        ]

        return QueryDecomposition(sub_queries=sub_queries)
