from agentic_rag.llm.interface import LLM
from agentic_rag.llm.structured import generate_structured
from agentic_rag.models.decomposition import (
    LLMQueryDecomposition,
    QueryDecomposition,
    SubQuery,
)
from agentic_rag.models.query import QueryInput
from agentic_rag.prompts.decomposition import SYSTEM_PROMPT, build_decomposition_prompt


class LLMQueryDecomposer:
    def __init__(self, llm: LLM):
        self.llm = llm

    async def decompose(
        self,
        query_input: QueryInput,
    ) -> QueryDecomposition:
        prompt = build_decomposition_prompt(query_input.query)

        llm_decomposition = await generate_structured(
            self.llm,
            prompt=prompt,
            system_prompt=SYSTEM_PROMPT,
            model_type=LLMQueryDecomposition,
        )

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
