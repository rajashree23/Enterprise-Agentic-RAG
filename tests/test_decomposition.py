from agentic_rag.models.decomposition import QueryDecomposition, SubQuery


def test_query_decomposition():
    decomposition = QueryDecomposition(
        sub_queries=[
            SubQuery(
                sub_query_id="sq-1",
                sub_query="What is the current project status?",
            ),
            SubQuery(
                sub_query_id="sq-2",
                sub_query="What are the outstanding issues?",
            ),
        ]
    )

    assert len(decomposition.sub_queries) == 2
    assert decomposition.sub_queries[0].sub_query_id == "sq-1"
    assert decomposition.sub_queries[1].sub_query == "What are the outstanding issues?"
