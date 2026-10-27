from agentic_rag.llm.interface import LLM
from agentic_rag.llm.structured import generate_structured
from agentic_rag.models.decomposition import QueryDecomposition
from agentic_rag.models.evidence_assessment import EvidenceAssessment
from agentic_rag.models.execution_plan import (
    ExecutionPlan,
    ExecutionStep,
    LLMExecutionPlan,
)
from agentic_rag.models.planning import (
    LLMPlanningDecision,
    PlanningDecision,
    PlanningOutcome,
)
from agentic_rag.prompts.planning import (
    PLANNING_DECISION_SYSTEM_PROMPT,
    PLANNING_SYSTEM_PROMPT,
    build_planning_decision_prompt,
    build_planning_prompt,
)
from agentic_rag.tools.argument_validator import validate_arguments
from agentic_rag.tools.registry import CapabilityRegistry


class PlanningArgumentError(ValueError):
    """An executable plan contains arguments that need user clarification."""

    def __init__(self, capability: str, message: str) -> None:
        super().__init__(message)
        self.capability = capability
        self.question = (
            f"Please provide valid required details for '{capability}'. {message}"
        )


class PlanningCapabilityError(ValueError):
    """An executable plan refers to a capability that is not registered."""


class LLMQueryPlanner:
    def __init__(
        self,
        llm: LLM,
        registry: CapabilityRegistry,
    ) -> None:
        self.llm = llm
        self.registry = registry

    async def create_planning_decision(
        self,
        decomposition: QueryDecomposition,
    ) -> PlanningDecision:
        sub_queries, capability_descriptions = self._planning_context(decomposition)
        prompt = build_planning_decision_prompt(
            sub_queries,
            capability_descriptions,
        )

        llm_decision = await generate_structured(
            self.llm,
            prompt=prompt,
            system_prompt=PLANNING_DECISION_SYSTEM_PROMPT,
            model_type=LLMPlanningDecision,
        )

        plan = None
        if llm_decision.outcome == PlanningOutcome.EXECUTABLE:
            if llm_decision.execution_plan is None:
                raise ValueError("Executable decisions require an execution plan")
            try:
                plan = self._to_execution_plan(
                    llm_decision.execution_plan,
                    decomposition,
                )
            except PlanningArgumentError as exc:
                return PlanningDecision(
                    outcome=PlanningOutcome.CLARIFICATION_REQUIRED,
                    reason=str(exc),
                    clarification_question=exc.question,
                )
            except PlanningCapabilityError as exc:
                return PlanningDecision(
                    outcome=PlanningOutcome.UNSUPPORTED,
                    reason=str(exc),
                )

        return PlanningDecision(
            outcome=llm_decision.outcome,
            reason=llm_decision.reason,
            plan=plan,
            clarification_question=llm_decision.clarification_question,
        )

    async def create_correction_plan(
        self,
        decomposition: QueryDecomposition,
        assessment: EvidenceAssessment,
        previous_plan: ExecutionPlan,
    ) -> ExecutionPlan:
        correction_context = {
            "assessment": assessment.model_dump(mode="json"),
            "previous_plan": previous_plan.model_dump(mode="json"),
        }

        return await self._create_plan(
            decomposition,
            correction_context=correction_context,
        )

    async def _create_plan(
        self,
        decomposition: QueryDecomposition,
        correction_context: dict | None = None,
    ) -> ExecutionPlan:
        sub_queries, capability_descriptions = self._planning_context(decomposition)

        if not capability_descriptions:
            raise ValueError(
                "Cannot create an execution plan without registered capabilities"
            )

        prompt = build_planning_prompt(
            sub_queries,
            capability_descriptions,
            correction_context=correction_context,
        )

        llm_plan = await generate_structured(
            self.llm,
            prompt=prompt,
            system_prompt=PLANNING_SYSTEM_PROMPT,
            model_type=LLMExecutionPlan,
        )

        return self._to_execution_plan(llm_plan, decomposition)

    def _planning_context(
        self,
        decomposition: QueryDecomposition,
    ) -> tuple[list[dict], list[dict]]:
        sub_queries = [
            sub_query.model_dump(mode="json") for sub_query in decomposition.sub_queries
        ]

        capabilities = self.registry.list_capabilities()
        capability_descriptions = [
            capability.model_dump(mode="json") for capability in capabilities
        ]

        return sub_queries, capability_descriptions

    def _to_execution_plan(
        self,
        llm_plan: LLMExecutionPlan,
        decomposition: QueryDecomposition,
    ) -> ExecutionPlan:
        known_sub_query_ids = {
            sub_query.sub_query_id for sub_query in decomposition.sub_queries
        }

        planned_sub_query_ids = [step.sub_query_id for step in llm_plan.execution_steps]
        planned_step_keys = [step.step_key for step in llm_plan.execution_steps]

        # 1. Reject unknown sub-query IDs.
        for sub_query_id in planned_sub_query_ids:
            if sub_query_id not in known_sub_query_ids:
                raise ValueError(f"Unknown sub_query_id: {sub_query_id}")

        # 2. Step keys must be unique even when a sub-query needs several steps.
        if len(planned_step_keys) != len(set(planned_step_keys)):
            raise ValueError("Duplicate execution step_key")

        # 3. Ensure every sub-query is covered at least once.
        if set(planned_sub_query_ids) != known_sub_query_ids:
            raise ValueError("Execution plan must cover every sub-query")

        # 4. Validate capabilities and dependencies.
        registered_capabilities = {
            capability.name for capability in self.registry.list_capabilities()
        }

        for planned_step in llm_plan.execution_steps:
            if planned_step.capability not in registered_capabilities:
                raise PlanningCapabilityError(
                    f"Unsupported capability: {planned_step.capability}"
                )

            try:
                validate_arguments(
                    self.registry.get_capability(planned_step.capability),
                    planned_step.arguments,
                )
            except (ValueError, TypeError) as exc:
                raise PlanningArgumentError(
                    planned_step.capability,
                    str(exc),
                ) from exc

            if planned_step.step_key in planned_step.depends_on_step_keys:
                raise ValueError(
                    f"Step cannot depend on itself: {planned_step.step_key}"
                )

            if len(planned_step.depends_on_step_keys) != len(
                set(planned_step.depends_on_step_keys)
            ):
                raise ValueError(f"Duplicate dependencies for {planned_step.step_key}")

            for dependency in planned_step.depends_on_step_keys:
                if dependency not in planned_step_keys:
                    raise ValueError(f"Unknown dependency step_key: {dependency}")

        # 5. Detect dependency cycles before translating IDs.
        dependencies_by_step_key = {
            step.step_key: step.depends_on_step_keys
            for step in llm_plan.execution_steps
        }

        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(step_key: str) -> None:
            if step_key in visiting:
                raise ValueError("Circular dependency detected")

            if step_key in visited:
                return

            visiting.add(step_key)

            for dependency in dependencies_by_step_key[step_key]:
                visit(dependency)

            visiting.remove(step_key)
            visited.add(step_key)

        for step_key in dependencies_by_step_key:
            visit(step_key)

        # 6. Generate step IDs in the application.
        step_id_by_step_key = {
            step.step_key: f"step-{index}"
            for index, step in enumerate(llm_plan.execution_steps, start=1)
        }

        execution_steps = [
            ExecutionStep(
                step_id=step_id_by_step_key[planned_step.step_key],
                sub_query_id=planned_step.sub_query_id,
                action=planned_step.action,
                capability=planned_step.capability,
                arguments=planned_step.arguments,
                depends_on=[
                    step_id_by_step_key[dependency]
                    for dependency in planned_step.depends_on_step_keys
                ],
            )
            for planned_step in llm_plan.execution_steps
        ]

        return ExecutionPlan(execution_steps=execution_steps)
