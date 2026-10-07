from agentic_rag.llm.interface import LLM
from agentic_rag.models.decomposition import QueryDecomposition
from agentic_rag.models.execution_plan import (
    ExecutionPlan,
    ExecutionStep,
    LLMExecutionPlan,
)


class LLMQueryPlanner:
    def __init__(self, llm: LLM):
        self.llm = llm

    async def create_plan(
        self,
        decomposition: QueryDecomposition,
    ) -> ExecutionPlan:
        sub_queries = "\n".join(
            f"- {sub_query.sub_query_id}: {sub_query.sub_query}"
            for sub_query in decomposition.sub_queries
        )

        prompt = f"""
You are an execution planning system.

Create an execution plan for the following sub-queries.

Sub-queries:
{sub_queries}

Rules:
1. Return ONLY valid JSON.
2. Every execution step must reference an existing sub_query_id.
3. Do not invent sub_query_id values.
4. dependencies must reference existing sub_query_id values.
5. Use an empty dependency list when a step can run independently.
6. capability must be a logical capability such as:
   - github.search
   - slack.search
   - notion.search
7. Do not include step_id. The application will generate step IDs.

Return exactly this structure:

{{
  "execution_steps": [
    {{
      "sub_query_id": "sq-1",
      "action": "description of action",
      "capability": "github.search",
      "depends_on_sub_query_ids": []
    }}
  ]
}}
"""

        response = await self.llm.generate(prompt)

        llm_plan = LLMExecutionPlan.model_validate_json(response)

        return self._to_execution_plan(
            llm_plan,
            decomposition,
        )

    def _to_execution_plan(
        self,
        llm_plan: LLMExecutionPlan,
        decomposition: QueryDecomposition,
    ) -> ExecutionPlan:
        known_sub_query_ids = {
            sub_query.sub_query_id for sub_query in decomposition.sub_queries
        }

        for planned_step in llm_plan.execution_steps:
            if planned_step.sub_query_id not in known_sub_query_ids:
                raise ValueError(f"Unknown sub_query_id: {planned_step.sub_query_id}")

            for dependency in planned_step.depends_on_sub_query_ids:
                if dependency not in known_sub_query_ids:
                    raise ValueError(f"Unknown dependency sub_query_id: {dependency}")

        step_id_by_sub_query_id = {
            sub_query_id: f"step-{index}"
            for index, sub_query_id in enumerate(
                (sub_query.sub_query_id for sub_query in decomposition.sub_queries),
                start=1,
            )
        }

        execution_steps = []

        for planned_step in llm_plan.execution_steps:
            execution_steps.append(
                ExecutionStep(
                    step_id=step_id_by_sub_query_id[planned_step.sub_query_id],
                    sub_query_id=planned_step.sub_query_id,
                    action=planned_step.action,
                    capability=planned_step.capability,
                    depends_on=[
                        step_id_by_sub_query_id[dependency]
                        for dependency in planned_step.depends_on_sub_query_ids
                    ],
                )
            )

        return ExecutionPlan(
            execution_steps=execution_steps,
        )
