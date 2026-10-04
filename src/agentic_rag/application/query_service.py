from agentic_rag.decomposer.decomposer import decompose_query
from agentic_rag.models.execution_plan import ExecutionPlan
from agentic_rag.models.query import QueryInput
from agentic_rag.planner.planner import create_plan


def process_query(query_input: QueryInput) -> ExecutionPlan:
    decomposition = decompose_query(query_input)
    return create_plan(decomposition)
