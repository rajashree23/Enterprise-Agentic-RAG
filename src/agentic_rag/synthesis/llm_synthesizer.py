from agentic_rag.assessment.validation import validate_assessment_references
from agentic_rag.llm.interface import LLM
from agentic_rag.models.evidence import Evidence
from agentic_rag.models.evidence_assessment import (
    AssessmentStatus,
    EvidenceAssessment,
)
from agentic_rag.models.query import QueryInput
from agentic_rag.models.synthesis import Synthesis
from agentic_rag.prompts.synthesis import build_synthesis_prompt
from agentic_rag.synthesis.validation import validate_synthesis_references


class LLMAnswerSynthesizer:
    def __init__(self, llm: LLM):
        self.llm = llm

    async def synthesize(
        self,
        *,
        query_input: QueryInput,
        assessment: EvidenceAssessment,
        evidence: list[Evidence],
    ) -> Synthesis:
        if assessment.status == AssessmentStatus.INSUFFICIENT:
            raise ValueError("Cannot synthesize from insufficient evidence")

        available_ids = {item.evidence_id for item in evidence}

        validate_assessment_references(assessment, available_ids)

        relevant_ids = set(assessment.relevant_evidence_ids)
        selected_evidence = [
            item for item in evidence if item.evidence_id in relevant_ids
        ]

        prompt = build_synthesis_prompt(
            query_input=query_input,
            assessment=assessment,
            evidence=selected_evidence,
        )

        response = await self.llm.generate(prompt)
        synthesis = Synthesis.model_validate_json(response)

        allowed_ids = {item.evidence_id for item in selected_evidence}
        validate_synthesis_references(synthesis, allowed_ids)

        limitations = [
            *synthesis.limitations,
            *assessment.gaps,
        ]

        if assessment.status == AssessmentStatus.PARTIAL:
            limitations.append("The available evidence supports only a partial answer.")

        synthesis.limitations = list(dict.fromkeys(limitations))

        return synthesis
