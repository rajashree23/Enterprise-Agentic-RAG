from fastapi import APIRouter

from agentic_rag.application.query_service import process_query
from agentic_rag.composition import (
    create_decomposer,
    create_executor,
    create_planner,
)
from agentic_rag.models.execution_result import ExecutionResults
from agentic_rag.models.query import QueryInput

router = APIRouter()


@router.post("/query", response_model=ExecutionResults)
def query(query_input: QueryInput) -> ExecutionResults:
    decomposer = create_decomposer()
    planner = create_planner()
    executor = create_executor()

    return process_query(
        query_input,
        decomposer,
        planner,
        executor,
    )
