from fastapi import APIRouter

from agentic_rag.application.query_service import process_query
from agentic_rag.composition import (
    create_assessor,
    create_decomposer,
    create_executor,
    create_normalizers,
    create_planner,
    create_synthesizer,
)
from agentic_rag.models.query import QueryInput, QueryResponse

router = APIRouter()


@router.post("/query", response_model=QueryResponse)
async def query(query_input: QueryInput) -> QueryResponse:
    return await process_query(
        query_input=query_input,
        decomposer=create_decomposer(),
        planner=create_planner(),
        executor=create_executor(),
        normalizers=create_normalizers(),
        assessor=create_assessor(),
        synthesizer=create_synthesizer(),
    )
