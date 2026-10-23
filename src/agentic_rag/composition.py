from agentic_rag.decomposer.llm_decomposer import LLMQueryDecomposer
from agentic_rag.execution.executor import DeterministicExecutionEngine
from agentic_rag.execution.tool_operation import ToolExecutionOperation
from agentic_rag.llm.lm_studio import LMStudioLLM
from agentic_rag.models.capability import CapabilityDefinition
from agentic_rag.planner.llm_planner import LLMQueryPlanner
from agentic_rag.tools.github import GitHubSearchTool
from agentic_rag.tools.registry import CapabilityRegistry


def create_llm() -> LMStudioLLM:
    return LMStudioLLM(temperature=0.0)


def create_decomposer() -> LLMQueryDecomposer:
    return LLMQueryDecomposer(create_llm())


def create_registry() -> CapabilityRegistry:
    registry = CapabilityRegistry()

    registry.register(
        CapabilityDefinition(
            name="github.search",
            description="Search GitHub issues and pull requests.",
            arguments={"query": "string"},
        ),
        GitHubSearchTool(),
    )

    return registry


def create_planner(
    registry: CapabilityRegistry | None = None,
) -> LLMQueryPlanner:
    if registry is None:
        registry = create_registry()

    return LLMQueryPlanner(create_llm(), registry)


def create_executor(
    registry: CapabilityRegistry | None = None,
) -> DeterministicExecutionEngine:
    if registry is None:
        registry = create_registry()

    operation = ToolExecutionOperation(registry)
    return DeterministicExecutionEngine(operation)
