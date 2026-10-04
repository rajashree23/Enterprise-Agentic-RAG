from agentic_rag.decomposer.interface import QueryDecomposer
from agentic_rag.models.execution_plan import ExecutionPlan
from agentic_rag.models.query import QueryInput
from agentic_rag.planner.planner import create_plan


def process_query(
    query_input: QueryInput,
    decomposer: QueryDecomposer,
) -> ExecutionPlan:
    decomposition = decomposer.decompose(query_input)

    return create_plan(decomposition)
