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
    ) -> str:
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                }
            ],
            temperature=self.temperature,
        )

        return response.choices[0].message.content or ""
