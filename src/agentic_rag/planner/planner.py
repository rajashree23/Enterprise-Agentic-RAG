from agentic_rag.models.decomposition import QueryDecomposition
from agentic_rag.models.execution_plan import ExecutionPlan, ExecutionStep


class DeterministicQueryPlanner:
    async def create_plan(
        self,
        decomposition: QueryDecomposition,
    ) -> ExecutionPlan:
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
                    depends_on=[],
                )
            )

        return ExecutionPlan(execution_steps=execution_steps)
