from agentic_rag.composition import create_decomposer
from agentic_rag.models.query import QueryInput


# async def test_real_llm_decomposition():
#     decomposer = create_decomposer()

#     result = await decomposer.decompose(
#         QueryInput(query="What is the status and owner of Project X?")
#     )

#     assert len(result.sub_queries) >= 1

#     for sub_query in result.sub_queries:
#         assert sub_query.sub_query_id
#         assert sub_query.sub_query.strip()
