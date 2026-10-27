from typing import Any

from openai import AsyncOpenAI


class LMStudioLLM:
    def __init__(
        self,
        base_url: str = "http://localhost:1234/v1",
        api_key: str = "lm-studio",
        model: str = "qwen/qwen3-8b",
        temperature: float = 0.0,
    ):
        self.model = model
        self.temperature = temperature

        self.client = AsyncOpenAI(
            base_url=base_url,
            api_key=api_key,
        )

    async def generate(
        self,
        prompt: str,
        *,
        system_prompt: str | None = None,
        response_schema: dict[str, Any] | None = None,
    ) -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response_format = None
        if response_schema is not None:
            response_format = {
                "type": "json_schema",
                "json_schema": {
                    "name": "structured_response",
                    "strict": True,
                    "schema": response_schema,
                },
            }

        request: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
        }
        if response_format is not None:
            request["response_format"] = response_format

        response = await self.client.chat.completions.create(**request)

        return response.choices[0].message.content or ""
