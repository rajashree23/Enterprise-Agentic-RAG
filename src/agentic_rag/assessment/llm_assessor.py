from agentic_rag.assessment.validation import validate_assessment_references
from agentic_rag.llm.interface import LLM
from agentic_rag.models.decomposition import QueryDecomposition
from agentic_rag.models.evidence import Evidence
from agentic_rag.models.evidence_assessment import (
    AssessmentStatus,
    EvidenceAssessment,
)
from agentic_rag.models.execution_plan import ExecutionPlan
from agentic_rag.models.execution_result import ExecutionResult
from agentic_rag.models.query import NormalizationWarning, QueryInput
from agentic_rag.prompts.evidence_assessment import (
    build_evidence_assessment_prompt,
)


class LLMEvidenceAssessor:
    def __init__(self, llm: LLM):
        self.llm = llm

    async def assess(
        self,
        *,
        query_input: QueryInput,
        evidence: list[Evidence],
        execution_results: list[ExecutionResult],
        normalization_warnings: list[NormalizationWarning],
        decomposition: QueryDecomposition | None = None,
        plan: ExecutionPlan | None = None,
    ) -> EvidenceAssessment:
        if not evidence:
            return EvidenceAssessment(
                status=AssessmentStatus.INSUFFICIENT,
                reason="No normalized evidence is available to assess.",
                relevant_evidence_ids=[],
                gaps=["Supporting evidence for the question is unavailable."],
            )

        prompt = build_evidence_assessment_prompt(
            query_input=query_input,
            evidence=evidence,
            execution_results=execution_results,
            normalization_warnings=normalization_warnings,
            decomposition=decomposition,
            plan=plan,
        )

        response = await self.llm.generate(prompt)

        assessment = EvidenceAssessment.model_validate_json(response)

        available_evidence_ids = {item.evidence_id for item in evidence}

        validate_assessment_references(
            assessment,
            available_evidence_ids,
        )

        return assessment
