from agentic_rag.decomposer.llm_decomposer import LLMQueryDecomposer
from agentic_rag.execution.executor import DeterministicExecutionEngine
from agentic_rag.execution.operations import DeterministicExecutionOperation
from agentic_rag.llm.lm_studio import LMStudioLLM
from agentic_rag.planner.llm_planner import LLMQueryPlanner


def create_llm() -> LMStudioLLM:
    return LMStudioLLM(
        temperature=0.0,
    )


def create_decomposer() -> LLMQueryDecomposer:
    return LLMQueryDecomposer(create_llm())


def create_planner() -> LLMQueryPlanner:
    return LLMQueryPlanner(create_llm())


def create_executor() -> DeterministicExecutionEngine:
    operation = DeterministicExecutionOperation()
    return DeterministicExecutionEngine(operation)
