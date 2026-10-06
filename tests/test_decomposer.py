from agentic_rag.decomposer.decomposer import DeterministicQueryDecomposer
from agentic_rag.models.query import QueryInput


async def test_decompose_query():
    query = QueryInput(
        query="What is the status of Project X?",
    )

    decomposer = DeterministicQueryDecomposer()

    decomposition = await decomposer.decompose(query)

    assert len(decomposition.sub_queries) == 1
    assert decomposition.sub_queries[0].sub_query_id == "sq-1"
    assert decomposition.sub_queries[0].sub_query == "What is the status of Project X?"
