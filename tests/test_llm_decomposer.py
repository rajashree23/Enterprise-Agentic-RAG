from agentic_rag.decomposer.llm_decomposer import LLMQueryDecomposer
from agentic_rag.llm.structured import generate_structured
from agentic_rag.models.planning import LLMPlanningDecision
from agentic_rag.models.query import QueryInput


class FakeLLM:
    async def generate(
        self,
        prompt: str,
        *,
        system_prompt: str | None = None,
        response_schema: dict | None = None,
    ) -> str:
        return """
        {
            "sub_queries": [
                {
                    "sub_query": "Find the current status of Project X"
                },
                {
                    "sub_query": "Find the owner of Project X"
                }
            ]
        }
        """


async def test_llm_decomposer_creates_sub_queries():
    llm = FakeLLM()
    decomposer = LLMQueryDecomposer(llm)

    query = QueryInput(query="What is the status and owner of Project X?")

    result = await decomposer.decompose(query)

    assert len(result.sub_queries) == 2

    assert result.sub_queries[0].sub_query_id == "sq-1"
    assert result.sub_queries[0].sub_query == "Find the current status of Project X"

    assert result.sub_queries[1].sub_query_id == "sq-2"
    assert result.sub_queries[1].sub_query == "Find the owner of Project X"


async def test_llm_decomposer_repairs_invalid_json_once():
    class RepairingLLM:
        def __init__(self):
            self.responses = iter(
                [
                    "not json",
                    '{"sub_queries": [{"sub_query": "Find Project X status"}]}',
                ]
            )
            self.prompts = []

        async def generate(
            self,
            prompt: str,
            *,
            system_prompt: str | None = None,
            response_schema: dict | None = None,
        ) -> str:
            self.prompts.append(prompt)
            return next(self.responses)

    llm = RepairingLLM()
    result = await LLMQueryDecomposer(llm).decompose(
        QueryInput(query="Find Project X status")
    )

    assert result.sub_queries[0].sub_query == "Find Project X status"
    assert len(llm.prompts) == 2
    assert "Repair the invalid response" in llm.prompts[1]


async def test_structured_generation_repairs_model_validation_error():
    class RepairingLLM:
        def __init__(self):
            self.responses = iter(
                [
                    """{
                        "outcome": "clarification_required",
                        "reason": "A required value is missing.",
                        "execution_plan": {"execution_steps": []},
                        "clarification_question": "Which value?"
                    }""",
                    """{
                        "outcome": "clarification_required",
                        "reason": "A required value is missing.",
                        "execution_plan": null,
                        "clarification_question": "Which value?"
                    }""",
                ]
            )
            self.prompts: list[str] = []

        async def generate(
            self,
            prompt: str,
            *,
            system_prompt: str | None = None,
            response_schema: dict | None = None,
        ) -> str:
            self.prompts.append(prompt)
            return next(self.responses)

    llm = RepairingLLM()
    result = await generate_structured(
        llm,
        prompt="context",
        system_prompt="rules",
        model_type=LLMPlanningDecision,
    )

    assert result.execution_plan is None
    assert len(llm.prompts) == 2
    assert "Only executable decisions may contain an execution plan" in llm.prompts[1]
