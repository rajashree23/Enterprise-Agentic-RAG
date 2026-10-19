from agentic_rag.llm.interface import LLM
from agentic_rag.models.decomposition import QueryDecomposition
from agentic_rag.models.execution_plan import (
    ExecutionPlan,
    ExecutionStep,
    LLMExecutionPlan,
)
from agentic_rag.prompts.planning import build_planning_prompt
from agentic_rag.tools.registry import CapabilityRegistry


class LLMQueryPlanner:
    def __init__(
        self,
        llm: LLM,
        registry: CapabilityRegistry,
    ) -> None:
        self.llm = llm
        self.registry = registry

    async def create_plan(
        self,
        decomposition: QueryDecomposition,
    ) -> ExecutionPlan:
        sub_queries = "\n".join(
            f"- {sub_query.sub_query_id}: {sub_query.sub_query}"
            for sub_query in decomposition.sub_queries
        )

        capabilities = self.registry.list_capabilities()

        capability_descriptions = "\n".join(
            (
                f"- {capability.name}: {capability.description}; "
                f"arguments: {capability.arguments}"
            )
            for capability in capabilities
        )

        if not capability_descriptions:
            raise ValueError(
                "Cannot create an execution plan without registered capabilities"
            )

        prompt = build_planning_prompt(
            sub_queries,
            capability_descriptions,
        )

        response = await self.llm.generate(prompt)
        llm_plan = LLMExecutionPlan.model_validate_json(response)

        return self._to_execution_plan(llm_plan, decomposition)

    def _to_execution_plan(
        self,
        llm_plan: LLMExecutionPlan,
        decomposition: QueryDecomposition,
    ) -> ExecutionPlan:
        known_sub_query_ids = {
            sub_query.sub_query_id for sub_query in decomposition.sub_queries
        }

        planned_sub_query_ids = [step.sub_query_id for step in llm_plan.execution_steps]

        # 1. Reject unknown sub-query IDs.
        for sub_query_id in planned_sub_query_ids:
            if sub_query_id not in known_sub_query_ids:
                raise ValueError(f"Unknown sub_query_id: {sub_query_id}")

        # 2. Reject duplicate execution steps.
        if len(planned_sub_query_ids) != len(set(planned_sub_query_ids)):
            raise ValueError("Duplicate execution steps for a sub-query")

        # 3. Ensure every sub-query is covered exactly once.
        if set(planned_sub_query_ids) != known_sub_query_ids:
            raise ValueError("Execution plan must cover every sub-query exactly once")

        # 4. Validate capabilities and dependencies.
        registered_capabilities = {
            capability.name for capability in self.registry.list_capabilities()
        }

        for planned_step in llm_plan.execution_steps:
            if planned_step.capability not in registered_capabilities:
                raise ValueError(f"Unsupported capability: {planned_step.capability}")

            if planned_step.sub_query_id in planned_step.depends_on_sub_query_ids:
                raise ValueError(
                    f"Step cannot depend on itself: {planned_step.sub_query_id}"
                )

            if len(planned_step.depends_on_sub_query_ids) != len(
                set(planned_step.depends_on_sub_query_ids)
            ):
                raise ValueError(
                    f"Duplicate dependencies for {planned_step.sub_query_id}"
                )

            for dependency in planned_step.depends_on_sub_query_ids:
                if dependency not in known_sub_query_ids:
                    raise ValueError(f"Unknown dependency sub_query_id: {dependency}")

        # 5. Detect dependency cycles before translating IDs.
        dependencies_by_sub_query_id = {
            step.sub_query_id: step.depends_on_sub_query_ids
            for step in llm_plan.execution_steps
        }

        visiting: set[str] = set()
        visited: set[str] = set()

        def visit(sub_query_id: str) -> None:
            if sub_query_id in visiting:
                raise ValueError("Circular dependency detected")

            if sub_query_id in visited:
                return

            visiting.add(sub_query_id)

            for dependency in dependencies_by_sub_query_id[sub_query_id]:
                visit(dependency)

            visiting.remove(sub_query_id)
            visited.add(sub_query_id)

        for sub_query_id in dependencies_by_sub_query_id:
            visit(sub_query_id)

        # 6. Generate step IDs in the application.
        step_id_by_sub_query_id = {
            sub_query.sub_query_id: f"step-{index}"
            for index, sub_query in enumerate(
                decomposition.sub_queries,
                start=1,
            )
        }

        execution_steps = [
            ExecutionStep(
                step_id=step_id_by_sub_query_id[planned_step.sub_query_id],
                sub_query_id=planned_step.sub_query_id,
                action=planned_step.action,
                capability=planned_step.capability,
                arguments=planned_step.arguments,
                depends_on=[
                    step_id_by_sub_query_id[dependency]
                    for dependency in planned_step.depends_on_sub_query_ids
                ],
            )
            for planned_step in llm_plan.execution_steps
        ]

        return ExecutionPlan(execution_steps=execution_steps)
