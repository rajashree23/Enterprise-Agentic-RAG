from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from agentic_rag.models.citation import ResolvedCitation
from agentic_rag.models.direct_answer import DirectAnswer
from agentic_rag.models.evidence import Evidence
from agentic_rag.models.evidence_assessment import (
    AssessmentStatus,
    EvidenceAssessment,
)
from agentic_rag.models.execution_result import ExecutionResult
from agentic_rag.models.planning import PlanningOutcome
from agentic_rag.models.synthesis import Synthesis


class QueryInput(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
    )

    conversation_id: str | None = None
    query: str = Field(min_length=1)


class NormalizationWarning(BaseModel):
    step_id: str
    capability: str | None
    message: str


class AssessmentError(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: Literal["invalid_output", "unavailable"]
    message: str = Field(min_length=1)


class SynthesisError(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: Literal["invalid_output", "unavailable"]
    message: str = Field(min_length=1)


class DirectAnswerError(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: Literal["invalid_output", "unavailable"]
    message: str = Field(min_length=1)


class QueryResponse(BaseModel):
    execution_results: list[ExecutionResult]
    evidence: list[Evidence]
    normalization_warnings: list[NormalizationWarning]
    assessment: EvidenceAssessment | None = None
    assessment_error: AssessmentError | None = None
    synthesis: Synthesis | None = None
    synthesis_error: SynthesisError | None = None
    resolved_citations: list[ResolvedCitation] = Field(default_factory=list)
    planning_outcome: PlanningOutcome | None = None
    planning_reason: str | None = None
    clarification_question: str | None = None
    direct_answer: DirectAnswer | None = None
    direct_answer_error: DirectAnswerError | None = None

    @model_validator(mode="after")
    def validate_stage_outcomes(self) -> "QueryResponse":
        if self.planning_outcome == PlanningOutcome.CLARIFICATION_REQUIRED:
            if not self.clarification_question:
                raise ValueError(
                    "Clarification planning outcomes require a clarification question"
                )
        elif self.clarification_question is not None:
            raise ValueError(
                "Only clarification planning outcomes may contain a question"
            )

        if self.direct_answer is not None and self.direct_answer_error is not None:
            raise ValueError(
                "Direct answer and direct_answer_error cannot both be present"
            )

        if self.assessment is not None and self.assessment_error is not None:
            raise ValueError("Assessment and assessment_error cannot both be present")

        if self.synthesis is not None and self.synthesis_error is not None:
            raise ValueError("Synthesis and synthesis_error cannot both be present")

        has_synthesis_outcome = (
            self.synthesis is not None or self.synthesis_error is not None
        )

        if has_synthesis_outcome:
            if self.assessment is None:
                raise ValueError("A synthesis outcome requires an evidence assessment")

            if self.assessment.status == AssessmentStatus.INSUFFICIENT:
                raise ValueError(
                    "A synthesis outcome requires sufficient or partial evidence"
                )

        if self.resolved_citations and self.synthesis is None:
            raise ValueError("Resolved citations require a successful synthesis")

        return self
