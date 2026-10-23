from agentic_rag.decomposer.interface import QueryDecomposer
from agentic_rag.execution.interface import ExecutionEngine
from agentic_rag.models.execution_result import ExecutionResult
from agentic_rag.models.query import QueryInput
from agentic_rag.planner.interface import QueryPlanner


async def process_query(
    query_input: QueryInput,
    decomposer: QueryDecomposer,
    planner: QueryPlanner,
    executor: ExecutionEngine,
) -> ExecutionResult:
    decomposition = await decomposer.decompose(query_input)

    plan = await planner.create_plan(decomposition)

    return await executor.execute(plan)
