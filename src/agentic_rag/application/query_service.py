from agentic_rag.decomposer.interface import QueryDecomposer
from agentic_rag.execution.interface import ExecutionEngine
from agentic_rag.models.execution_plan import ExecutionPlan
from agentic_rag.models.query import QueryInput
from agentic_rag.planner.interface import QueryPlanner


def process_query(
    query_input: QueryInput,
    decomposer: QueryDecomposer,
    planner: QueryPlanner,
    executor: ExecutionEngine,
) -> ExecutionPlan:
    decomposition = decomposer.decompose(query_input)

    plan = planner.create_plan(decomposition)
    
    return executor.execute(plan)
