from agentic_rag.application.query_service import process_query
from agentic_rag.models.decomposition import QueryDecomposition, SubQuery
from agentic_rag.models.query import QueryInput


class FakeDecomposer:
    def decompose(self, query_input: QueryInput) -> QueryDecomposition:
        return QueryDecomposition(
            sub_queries=[
                SubQuery(
                    sub_query_id="fake-sq-1",
                    sub_query="fake sub-query",
                )
            ]
        )


def test_process_query():
    query = QueryInput(
        query="What is the status of Project X?",
    )

    decomposer = FakeDecomposer()

    plan = process_query(query, decomposer)

    assert len(plan.execution_steps) == 1
    assert plan.execution_steps[0].step_id == "step-1"
    assert plan.execution_steps[0].sub_query_id == "fake-sq-1"
    assert plan.execution_steps[0].action == "fake sub-query"
