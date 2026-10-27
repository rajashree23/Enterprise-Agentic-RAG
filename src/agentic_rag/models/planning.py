from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator

from agentic_rag.models.execution_plan import ExecutionPlan, LLMExecutionPlan


class PlanningOutcome(StrEnum):
    EXECUTABLE = "executable"
    CLARIFICATION_REQUIRED = "clarification_required"
    UNSUPPORTED = "unsupported"
    NO_TOOL_REQUIRED = "no_tool_required"


class PlanningDecision(BaseModel):
    """Validated decision produced before the execution graph starts."""

    model_config = ConfigDict(extra="forbid")

    outcome: PlanningOutcome
    reason: str = Field(min_length=1)
    plan: ExecutionPlan | None = None
    clarification_question: str | None = None

    @model_validator(mode="after")
    def validate_outcome_fields(self) -> "PlanningDecision":
        if self.outcome == PlanningOutcome.EXECUTABLE:
            if self.plan is None:
                raise ValueError("Executable planning decisions require a plan")

            if self.clarification_question is not None:
                raise ValueError(
                    "Executable planning decisions cannot request clarification"
                )

        elif self.plan is not None:
            raise ValueError(
                "Only executable planning decisions may contain an execution plan"
            )

        if self.outcome == PlanningOutcome.CLARIFICATION_REQUIRED:
            if not self.clarification_question:
                raise ValueError(
                    "Clarification decisions require a clarification question"
                )
        elif self.clarification_question is not None:
            raise ValueError(
                "Only clarification decisions may contain a clarification question"
            )

        return self


class LLMPlanningDecision(BaseModel):
    """LLM-owned planning decision before application step-ID translation."""

    model_config = ConfigDict(extra="forbid")

    outcome: PlanningOutcome
    reason: str = Field(min_length=1)
    execution_plan: LLMExecutionPlan | None = None
    clarification_question: str | None = None

    @model_validator(mode="after")
    def validate_outcome_fields(self) -> "LLMPlanningDecision":
        if self.outcome == PlanningOutcome.EXECUTABLE:
            if self.execution_plan is None:
                raise ValueError("Executable decisions require an execution plan")

            if self.clarification_question is not None:
                raise ValueError("Executable decisions cannot request clarification")

        elif self.execution_plan is not None:
            raise ValueError("Only executable decisions may contain an execution plan")

        if self.outcome == PlanningOutcome.CLARIFICATION_REQUIRED:
            if not self.clarification_question:
                raise ValueError(
                    "Clarification decisions require a clarification question"
                )
        elif self.clarification_question is not None:
            raise ValueError(
                "Only clarification decisions may contain a clarification question"
            )

        return self
