from typing import Protocol


class LLM(Protocol):
    async def generate(
        self,
        prompt: str,
    ) -> str: ...
