from typing import Any, Protocol


class LLM(Protocol):
    async def generate(
        self,
        prompt: str,
        *,
        system_prompt: str | None = None,
        response_schema: dict[str, Any] | None = None,
    ) -> str: ...
