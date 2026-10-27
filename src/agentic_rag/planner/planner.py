from agentic_rag.models.decomposition import QueryDecomposition
from agentic_rag.models.execution_plan import ExecutionPlan, ExecutionStep
from agentic_rag.models.planning import PlanningDecision, PlanningOutcome


class DeterministicQueryPlanner:
    async def create_planning_decision(
        self,
        decomposition: QueryDecomposition,
    ) -> PlanningDecision:
        execution_steps = []

        for index, sub_query in enumerate(
            decomposition.sub_queries,
            start=1,
        ):
            execution_steps.append(
                ExecutionStep(
                    step_id=f"step-{index}",
                    sub_query_id=sub_query.sub_query_id,
                    action=sub_query.sub_query,
                    capability="default",
                    arguments={},
                    depends_on=[],
                )
            )

        return PlanningDecision(
            outcome=PlanningOutcome.EXECUTABLE,
            reason="The deterministic planner created an execution plan.",
            plan=ExecutionPlan(execution_steps=execution_steps),
        )
