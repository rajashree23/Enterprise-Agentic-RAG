from agentic_rag.decomposer.llm_decomposer import LLMQueryDecomposer
from agentic_rag.models.query import QueryInput


class FakeLLM:
    async def generate(self, prompt: str) -> str:
        return """
        {
            "sub_queries": [
                {
                    "sub_query": "Find the current status of Project X"
                },
                {
                    "sub_query": "Find the owner of Project X"
                }
            ]
        }
        """


async def test_llm_decomposer_creates_sub_queries():
    llm = FakeLLM()
    decomposer = LLMQueryDecomposer(llm)

    query = QueryInput(query="What is the status and owner of Project X?")

    result = await decomposer.decompose(query)

    assert len(result.sub_queries) == 2

    assert result.sub_queries[0].sub_query_id == "sq-1"
    assert result.sub_queries[0].sub_query == "Find the current status of Project X"

    assert result.sub_queries[1].sub_query_id == "sq-2"
    assert result.sub_queries[1].sub_query == "Find the owner of Project X"
