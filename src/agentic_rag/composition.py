from agentic_rag.assessment.llm_assessor import LLMEvidenceAssessor
from agentic_rag.decomposer.llm_decomposer import LLMQueryDecomposer
from agentic_rag.direct_answer.llm_generator import LLMDirectAnswerGenerator
from agentic_rag.evidence.github_comment import GitHubCommentNormalizer
from agentic_rag.evidence.github_issue import GitHubIssueNormalizer
from agentic_rag.evidence.interface import EvidenceNormalizer
from agentic_rag.execution.executor import DeterministicExecutionEngine
from agentic_rag.execution.tool_operation import ToolExecutionOperation
from agentic_rag.llm.lm_studio import LMStudioLLM
from agentic_rag.models.capability import CapabilityDefinition
from agentic_rag.planner.llm_planner import LLMQueryPlanner
from agentic_rag.synthesis.llm_synthesizer import LLMAnswerSynthesizer
from agentic_rag.tools.github.comments import GitHubIssueCommentsTool
from agentic_rag.tools.github.issue import GitHubIssueTool
from agentic_rag.tools.github.search import GitHubSearchTool
from agentic_rag.tools.registry import CapabilityRegistry


def create_normalizers() -> dict[str, EvidenceNormalizer]:
    return {
        "github.get_issue": GitHubIssueNormalizer(),
        "github.search": GitHubIssueNormalizer(capability="github.search"),
        "github.list_issue_comments": GitHubCommentNormalizer(),
    }


def create_llm() -> LMStudioLLM:
    return LMStudioLLM(temperature=0.0)


def create_decomposer() -> LLMQueryDecomposer:
    return LLMQueryDecomposer(create_llm())


def create_assessor() -> LLMEvidenceAssessor:
    return LLMEvidenceAssessor(create_llm())


def create_synthesizer() -> LLMAnswerSynthesizer:
    return LLMAnswerSynthesizer(create_llm())


def create_direct_answer_generator() -> LLMDirectAnswerGenerator:
    return LLMDirectAnswerGenerator(create_llm())


def create_registry() -> CapabilityRegistry:
    registry = CapabilityRegistry()

    registry.register(
        CapabilityDefinition(
            name="github.search",
            description=(
                "Search GitHub issues and pull requests. Results include record "
                "identifiers and each record's current open or closed state."
            ),
            arguments={"query": "string"},
        ),
        GitHubSearchTool(),
    )

    registry.register(
        CapabilityDefinition(
            name="github.get_issue",
            description=(
                "Retrieve issue or pull request details when the repository "
                "owner, repository name, and issue number are known. "
                "Does not retrieve discussion comments."
            ),
            arguments={
                "owner": "string",
                "repo": "string",
                "issue_number": "integer",
            },
        ),
        GitHubIssueTool(),
    )

    registry.register(
        CapabilityDefinition(
            name="github.list_issue_comments",
            description=(
                "Retrieve general discussion comments on an issue or pull "
                "request when the owner, repository, and number are known. "
                "Does not retrieve inline code-review comments. "
                "Retrieval is bounded and may leave additional pages unread."
            ),
            arguments={
                "owner": "string",
                "repo": "string",
                "issue_number": "integer",
            },
        ),
        GitHubIssueCommentsTool(),
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
