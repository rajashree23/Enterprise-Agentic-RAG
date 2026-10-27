from pydantic import ValidationError

from agentic_rag.llm.interface import LLM
from agentic_rag.models.direct_answer import DirectAnswer
from agentic_rag.models.query import QueryInput


class LLMDirectAnswerGenerator:
    def __init__(self, llm: LLM) -> None:
        self.llm = llm

    async def generate(
        self,
        *,
        query_input: QueryInput,
        planning_reason: str,
    ) -> DirectAnswer:
        prompt = f"""You answer a user question that does not require external tools.
Use your general knowledge only. Do not claim to have searched GitHub, Slack,
Notion, or any other external system. Return only valid JSON matching this schema:
{{"answer": "string"}}

Question:
{query_input.query}

Planning reason:
{planning_reason}
"""
        response = await self.llm.generate(prompt)
        try:
            return DirectAnswer.model_validate_json(response)
        except ValidationError as exc:
            raise ValueError(
                "Direct answer did not satisfy the response schema"
            ) from exc


__all__ = ["LLMDirectAnswerGenerator"]
