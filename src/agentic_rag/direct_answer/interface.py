from typing import Protocol

from agentic_rag.models.direct_answer import DirectAnswer
from agentic_rag.models.query import QueryInput


class DirectAnswerGenerator(Protocol):
    async def generate(
        self,
        *,
        query_input: QueryInput,
        planning_reason: str,
    ) -> DirectAnswer: ...
