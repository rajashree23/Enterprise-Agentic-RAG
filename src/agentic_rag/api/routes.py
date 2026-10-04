from fastapi import APIRouter

from agentic_rag.application.query_service import process_query
from agentic_rag.models.execution_plan import ExecutionPlan
from agentic_rag.models.query import QueryInput

router = APIRouter()


@router.post("/query", response_model=ExecutionPlan)
def query(query_input: QueryInput) -> ExecutionPlan:
    return process_query(query_input)
