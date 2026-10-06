from agentic_rag.decomposer.decomposer import DeterministicQueryDecomposer
from agentic_rag.execution.executor import DeterministicExecutionEngine
from agentic_rag.execution.operations import DeterministicExecutionOperation
from agentic_rag.planner.planner import DeterministicQueryPlanner


def create_decomposer() -> DeterministicQueryDecomposer:
    return DeterministicQueryDecomposer()


def create_planner() -> DeterministicQueryPlanner:
    return DeterministicQueryPlanner()


def create_executor() -> DeterministicExecutionEngine:
    operation = DeterministicExecutionOperation()

    return DeterministicExecutionEngine(operation)