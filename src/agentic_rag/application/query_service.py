import asyncio

from openai import APIError

from agentic_rag.assessment.interface import EvidenceAssessor
from agentic_rag.decomposer.interface import QueryDecomposer
from agentic_rag.evidence.interface import EvidenceNormalizer
from agentic_rag.execution.interface import ExecutionEngine
from agentic_rag.models.citation import ResolvedCitation
from agentic_rag.models.evidence import Evidence
from agentic_rag.models.evidence_assessment import (
    AssessmentStatus,
    EvidenceAssessment,
)
from agentic_rag.models.execution_result import ExecutionStatus
from agentic_rag.models.query import (
    AssessmentError,
    NormalizationWarning,
    QueryInput,
    QueryResponse,
    SynthesisError,
)
from agentic_rag.models.synthesis import Synthesis
from agentic_rag.planner.interface import QueryPlanner
from agentic_rag.synthesis.citation_resolution import resolve_citations
from agentic_rag.synthesis.interface import AnswerSynthesizer


async def process_query(
    query_input: QueryInput,
    decomposer: QueryDecomposer,
    planner: QueryPlanner,
    executor: ExecutionEngine,
    normalizers: dict[str, EvidenceNormalizer],
    assessor: EvidenceAssessor | None = None,
    synthesizer: AnswerSynthesizer | None = None,
) -> QueryResponse:
    # 1. Understand the question, create a plan, and execute tools.
    decomposition = await decomposer.decompose(query_input)
    plan = await planner.create_plan(decomposition)
    results = await executor.execute(plan)

    # 2. Convert successful tool results into normalized evidence.
    evidence: list[Evidence] = []
    warnings: list[NormalizationWarning] = []

    for result in results.execution_results:
        if result.status != ExecutionStatus.SUCCESS:
            continue

        capability = (
            result.tool_called.tool_id if result.tool_called is not None else None
        )

        normalizer = normalizers.get(capability) if capability else None

        if normalizer is None:
            warnings.append(
                NormalizationWarning(
                    step_id=result.step_id,
                    capability=capability,
                    message="No evidence normalizer is registered for this result.",
                )
            )
            continue

        try:
            normalized = normalizer.normalize(result)
        except ValueError:
            warnings.append(
                NormalizationWarning(
                    step_id=result.step_id,
                    capability=capability,
                    message="Tool output did not satisfy the evidence contract.",
                )
            )
            continue

        evidence.extend(normalized)

    # 3. Assess whether the evidence can answer the question.
    assessment: EvidenceAssessment | None = None
    assessment_error: AssessmentError | None = None

    if assessor is not None:
        try:
            assessment = await asyncio.wait_for(
                assessor.assess(
                    query_input=query_input,
                    evidence=evidence,
                    execution_results=results.execution_results,
                    normalization_warnings=warnings,
                    decomposition=decomposition,
                    plan=plan,
                ),
                timeout=60.0,
            )
        except ValueError:
            assessment_error = AssessmentError(
                code="invalid_output",
                message="The assessor returned an invalid assessment.",
            )
        except (APIError, TimeoutError):
            assessment_error = AssessmentError(
                code="unavailable",
                message="Evidence assessment could not be completed.",
            )

    # 4. Generate claims and resolve their citations.
    synthesis: Synthesis | None = None
    synthesis_error: SynthesisError | None = None
    resolved_citations: list[ResolvedCitation] = []

    answerable_statuses = {
        AssessmentStatus.SUFFICIENT,
        AssessmentStatus.PARTIAL,
    }

    if (
        synthesizer is not None
        and assessment is not None
        and assessment.status in answerable_statuses
    ):
        try:
            candidate_synthesis = await asyncio.wait_for(
                synthesizer.synthesize(
                    query_input=query_input,
                    assessment=assessment,
                    evidence=evidence,
                ),
                timeout=60.0,
            )

            candidate_citations = resolve_citations(
                candidate_synthesis,
                evidence,
            )

            synthesis = candidate_synthesis
            resolved_citations = candidate_citations

        except ValueError:
            synthesis_error = SynthesisError(
                code="invalid_output",
                message="Answer generation or citation resolution was invalid.",
            )
        except (APIError, TimeoutError):
            synthesis_error = SynthesisError(
                code="unavailable",
                message="Answer synthesis could not be completed.",
            )

    # 5. Preserve completed results even if a later stage failed.
    return QueryResponse(
        execution_results=results.execution_results,
        evidence=evidence,
        normalization_warnings=warnings,
        assessment=assessment,
        assessment_error=assessment_error,
        synthesis=synthesis,
        synthesis_error=synthesis_error,
        resolved_citations=resolved_citations,
    )
