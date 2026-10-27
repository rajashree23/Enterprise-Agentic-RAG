import asyncio
import hashlib
import json
from dataclasses import dataclass
from typing import Literal

from openai import APIError

from agentic_rag.assessment.interface import EvidenceAssessor
from agentic_rag.decomposer.interface import QueryDecomposer
from agentic_rag.direct_answer.interface import DirectAnswerGenerator
from agentic_rag.evidence.interface import EvidenceNormalizer
from agentic_rag.execution.interface import ExecutionEngine
from agentic_rag.models.evidence import Evidence
from agentic_rag.models.evidence_assessment import AssessmentStatus
from agentic_rag.models.execution_result import ExecutionStatus
from agentic_rag.models.planning import PlanningOutcome
from agentic_rag.models.query import (
    AssessmentError,
    DirectAnswerError,
    NormalizationWarning,
    SynthesisError,
)
from agentic_rag.orchestration.state import AgentState
from agentic_rag.planner.interface import QueryPlanner, QueryReplanner
from agentic_rag.synthesis.citation_resolution import resolve_citations
from agentic_rag.synthesis.interface import AnswerSynthesizer


@dataclass(frozen=True)
class QueryGraphDependencies:
    decomposer: QueryDecomposer
    planner: QueryPlanner
    executor: ExecutionEngine
    normalizers: dict[str, EvidenceNormalizer]
    replanner: QueryReplanner | None = None
    direct_answer_generator: DirectAnswerGenerator | None = None
    assessor: EvidenceAssessor | None = None
    synthesizer: AnswerSynthesizer | None = None
    stage_timeout_seconds: float = 60.0
    max_correction_attempts: int = 1

    def __post_init__(self) -> None:
        if self.stage_timeout_seconds <= 0:
            raise ValueError("stage_timeout_seconds must be positive")

        if self.max_correction_attempts < 0:
            raise ValueError("max_correction_attempts must be nonnegative")


class QueryGraphNodes:
    def __init__(self, dependencies: QueryGraphDependencies):
        self.dependencies = dependencies

    async def decompose(self, state: AgentState) -> dict:
        decomposition = await self.dependencies.decomposer.decompose(
            state["query_input"]
        )
        return {"decomposition": decomposition}

    async def plan(self, state: AgentState) -> dict:
        decision = await self.dependencies.planner.create_planning_decision(
            state["decomposition"]
        )

        if decision.outcome != PlanningOutcome.EXECUTABLE:
            return {"planning_decision": decision}

        if decision.plan is None:
            raise ValueError("Executable planning decisions require a plan")

        return {
            "planning_decision": decision,
            "plan": decision.plan,
            "plan_fingerprint": self._plan_fingerprint(decision.plan),
        }

    async def execute(self, state: AgentState) -> dict:
        results = await self.dependencies.executor.execute(state["plan"])
        return {"execution_results": results}

    async def direct_answer(self, state: AgentState) -> dict:
        generator = self.dependencies.direct_answer_generator
        decision = state["planning_decision"]
        if generator is None:
            return {
                "direct_answer": None,
                "direct_answer_error": DirectAnswerError(
                    code="unavailable",
                    message="Direct answering is not configured.",
                ),
            }

        try:
            answer = await asyncio.wait_for(
                generator.generate(
                    query_input=state["query_input"],
                    planning_reason=decision.reason,
                ),
                timeout=self.dependencies.stage_timeout_seconds,
            )
        except ValueError:
            return {
                "direct_answer": None,
                "direct_answer_error": DirectAnswerError(
                    code="invalid_output",
                    message="Direct answer generation returned invalid output.",
                ),
            }
        except (APIError, TimeoutError):
            return {
                "direct_answer": None,
                "direct_answer_error": DirectAnswerError(
                    code="unavailable",
                    message="Direct answer generation could not be completed.",
                ),
            }

        return {"direct_answer": answer, "direct_answer_error": None}

    async def replan(self, state: AgentState) -> dict:
        replanner = self.dependencies.replanner
        assessment = state.get("assessment")

        if replanner is None or assessment is None:
            raise ValueError("A correction plan requires a replanner and assessment")

        plan = await replanner.create_correction_plan(
            state["decomposition"],
            assessment,
            state["plan"],
        )

        fingerprint = self._plan_fingerprint(plan)

        return {
            "plan": plan,
            "correction_attempts": state.get("correction_attempts", 0) + 1,
            "plan_fingerprint": fingerprint,
            "replan_changed": fingerprint != state.get("plan_fingerprint"),
        }

    @staticmethod
    def _plan_fingerprint(plan) -> str:
        canonical_plan = json.dumps(
            plan.model_dump(mode="json"),
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(canonical_plan.encode("utf-8")).hexdigest()

    def normalize(self, state: AgentState) -> dict:
        evidence: list[Evidence] = []
        warnings: list[NormalizationWarning] = []

        for result in state["execution_results"].execution_results:
            if result.status != ExecutionStatus.SUCCESS:
                continue

            capability = (
                result.tool_called.tool_id if result.tool_called is not None else None
            )
            normalizer = (
                self.dependencies.normalizers.get(capability) if capability else None
            )

            if normalizer is None:
                warnings.append(
                    NormalizationWarning(
                        step_id=result.step_id,
                        capability=capability,
                        message=(
                            "No evidence normalizer is registered for this result."
                        ),
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
                        message=("Tool output did not satisfy the evidence contract."),
                    )
                )
                continue

            evidence.extend(normalized)

        return {
            "evidence": evidence,
            "normalization_warnings": warnings,
        }

    async def assess(self, state: AgentState) -> dict:
        assessor = self.dependencies.assessor
        if assessor is None:
            return {
                "assessment": None,
                "assessment_error": None,
            }

        try:
            assessment = await asyncio.wait_for(
                assessor.assess(
                    query_input=state["query_input"],
                    evidence=state["evidence"],
                    execution_results=(state["execution_results"].execution_results),
                    normalization_warnings=state["normalization_warnings"],
                    decomposition=state["decomposition"],
                    plan=state["plan"],
                ),
                timeout=self.dependencies.stage_timeout_seconds,
            )
        except ValueError:
            return {
                "assessment": None,
                "assessment_error": AssessmentError(
                    code="invalid_output",
                    message="The assessor returned an invalid assessment.",
                ),
            }
        except (APIError, TimeoutError):
            return {
                "assessment": None,
                "assessment_error": AssessmentError(
                    code="unavailable",
                    message="Evidence assessment could not be completed.",
                ),
            }

        return {
            "assessment": assessment,
            "assessment_error": None,
        }

    def route_after_assessment(
        self,
        state: AgentState,
    ) -> Literal["synthesize", "replan", "end"]:
        assessment = state.get("assessment")
        answerable_statuses = {
            AssessmentStatus.SUFFICIENT,
            AssessmentStatus.PARTIAL,
        }

        if assessment is not None and assessment.status in answerable_statuses:
            if self.dependencies.synthesizer is not None:
                return "synthesize"
            return "end"

        if (
            assessment is not None
            and assessment.status == AssessmentStatus.INSUFFICIENT
            and self._has_successful_execution(state)
            and self.dependencies.replanner is not None
            and state.get("correction_attempts", 0)
            < state.get("max_correction_attempts", 0)
        ):
            return "replan"

        return "end"

    @staticmethod
    def route_after_plan(
        state: AgentState,
    ) -> Literal["execute", "direct_answer", "end"]:
        decision = state.get("planning_decision")
        if decision is None:
            return "end"
        if decision.outcome == PlanningOutcome.EXECUTABLE:
            return "execute"
        if decision.outcome == PlanningOutcome.NO_TOOL_REQUIRED:
            return "direct_answer"
        return "end"

    @staticmethod
    def _has_successful_execution(state: AgentState) -> bool:
        execution_results = state.get("execution_results")
        return bool(
            execution_results
            and any(
                result.status == ExecutionStatus.SUCCESS
                for result in execution_results.execution_results
            )
        )

    def route_after_replan(self, state: AgentState) -> Literal["execute", "end"]:
        if state.get("replan_changed", False):
            return "execute"

        return "end"

    async def synthesize(self, state: AgentState) -> dict:
        synthesizer = self.dependencies.synthesizer
        assessment = state["assessment"]

        if synthesizer is None or assessment is None:
            return {}

        try:
            synthesis = await asyncio.wait_for(
                synthesizer.synthesize(
                    query_input=state["query_input"],
                    assessment=assessment,
                    evidence=state["evidence"],
                ),
                timeout=self.dependencies.stage_timeout_seconds,
            )
            resolved_citations = resolve_citations(
                synthesis,
                state["evidence"],
            )
        except ValueError:
            return {
                "synthesis": None,
                "synthesis_error": SynthesisError(
                    code="invalid_output",
                    message=("Answer generation or citation resolution was invalid."),
                ),
                "resolved_citations": [],
            }
        except (APIError, TimeoutError):
            return {
                "synthesis": None,
                "synthesis_error": SynthesisError(
                    code="unavailable",
                    message="Answer synthesis could not be completed.",
                ),
                "resolved_citations": [],
            }

        return {
            "synthesis": synthesis,
            "synthesis_error": None,
            "resolved_citations": resolved_citations,
        }
