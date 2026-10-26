from unittest.mock import AsyncMock

from agentic_rag.application.query_service import process_query
from agentic_rag.assessment.interface import EvidenceAssessor
from agentic_rag.decomposer.decomposer import DeterministicQueryDecomposer
from agentic_rag.execution.executor import DeterministicExecutionEngine
from agentic_rag.execution.operations import DeterministicExecutionOperation
from agentic_rag.models.execution_result import ExecutionStatus
from agentic_rag.models.query import QueryInput
from agentic_rag.planner.planner import DeterministicQueryPlanner


async def test_process_query():
    query = QueryInput(
        query="What is the status of Project X?",
    )

    decomposer = DeterministicQueryDecomposer()
    planner = DeterministicQueryPlanner()
    operation = DeterministicExecutionOperation()
    executor = DeterministicExecutionEngine(operation)

    results = await process_query(
        query,
        decomposer,
        planner,
        executor,
        normalizers={},
    )

    assert len(results.execution_results) == 1

    result = results.execution_results[0]

    assert result.step_id == "step-1"
    assert result.sub_query_id == "sq-1"
    assert result.status == ExecutionStatus.SUCCESS
    assert results.evidence == []
    assert len(results.normalization_warnings) == 1


async def test_process_query_preserves_results_when_assessment_is_invalid():
    assessor = AsyncMock(spec=EvidenceAssessor)
    assessor.assess.side_effect = ValueError("Unknown evidence ID")

    response = await process_query(
        QueryInput(query="What is the status of Project X?"),
        DeterministicQueryDecomposer(),
        DeterministicQueryPlanner(),
        DeterministicExecutionEngine(DeterministicExecutionOperation()),
        normalizers={},
        assessor=assessor,
    )

    assert len(response.execution_results) == 1
    assert response.execution_results[0].status == ExecutionStatus.SUCCESS
    assert len(response.normalization_warnings) == 1

    assert response.assessment is None
    assert response.assessment_error is not None
    assert response.assessment_error.code == "invalid_output"

    assessor.assess.assert_awaited_once()
    arguments = assessor.assess.call_args.kwargs
    assert arguments["execution_results"] == response.execution_results
    assert arguments["normalization_warnings"] == response.normalization_warnings
    assert arguments["decomposition"].sub_queries[0].sub_query == (
        "What is the status of Project X?"
    )
    assert arguments["plan"].execution_steps[0].sub_query_id == "sq-1"
