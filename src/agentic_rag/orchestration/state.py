from typing import NotRequired, TypedDict

from agentic_rag.models.citation import ResolvedCitation
from agentic_rag.models.decomposition import QueryDecomposition
from agentic_rag.models.direct_answer import DirectAnswer
from agentic_rag.models.evidence import Evidence
from agentic_rag.models.evidence_assessment import EvidenceAssessment
from agentic_rag.models.execution_plan import ExecutionPlan
from agentic_rag.models.execution_result import ExecutionResults
from agentic_rag.models.planning import PlanningDecision
from agentic_rag.models.query import (
    AssessmentError,
    DirectAnswerError,
    NormalizationWarning,
    QueryInput,
    SynthesisError,
)
from agentic_rag.models.synthesis import Synthesis


class AgentState(TypedDict):
    """Ephemeral state for one query workflow execution."""

    query_input: QueryInput
    decomposition: NotRequired[QueryDecomposition]
    planning_decision: NotRequired[PlanningDecision]
    direct_answer: NotRequired[DirectAnswer | None]
    direct_answer_error: NotRequired[DirectAnswerError | None]
    plan: NotRequired[ExecutionPlan]
    execution_results: NotRequired[ExecutionResults]
    evidence: NotRequired[list[Evidence]]
    normalization_warnings: NotRequired[list[NormalizationWarning]]
    assessment: NotRequired[EvidenceAssessment | None]
    assessment_error: NotRequired[AssessmentError | None]
    synthesis: NotRequired[Synthesis | None]
    synthesis_error: NotRequired[SynthesisError | None]
    resolved_citations: NotRequired[list[ResolvedCitation]]
    correction_attempts: NotRequired[int]
    max_correction_attempts: NotRequired[int]
    plan_fingerprint: NotRequired[str]
    replan_changed: NotRequired[bool]
