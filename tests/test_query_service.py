from agentic_rag.application.query_service import process_query
from agentic_rag.decomposer.decomposer import DeterministicQueryDecomposer
from agentic_rag.execution.executor import DeterministicExecutionEngine
from agentic_rag.models.execution_result import ExecutionStatus
from agentic_rag.models.query import QueryInput
from agentic_rag.planner.planner import DeterministicQueryPlanner


def test_process_query():
    query = QueryInput(
        query="What is the status of Project X?",
    )

    decomposer = DeterministicQueryDecomposer()
    planner = DeterministicQueryPlanner()
    executor = DeterministicExecutionEngine()

    results = process_query(
        query,
        decomposer,
        planner,
        executor,
    )

    assert len(results.execution_results) == 1

    result = results.execution_results[0]

    assert result.step_id == "step-1"
    assert result.sub_query_id == "sq-1"
    assert result.status == ExecutionStatus.SUCCESS
