from agentic_rag.application.query_service import process_query
from agentic_rag.models.query import QueryInput


def test_process_query():
    query = QueryInput(
        query="What is the status of Project X?",
    )

    plan = process_query(query)

    assert len(plan.execution_steps) == 1
    assert plan.execution_steps[0].step_id == "step-1"
    assert plan.execution_steps[0].sub_query_id == "sq-1"
    assert plan.execution_steps[0].action == "What is the status of Project X?"
