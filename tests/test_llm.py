from agentic_rag.llm.interface import LLM


class FakeLLM:
    async def generate(self, prompt: str) -> str:
        return "fake response"


async def test_llm_interface():
    llm: LLM = FakeLLM()

    response = await llm.generate("Hello")

    assert response == "fake response"


from unittest.mock import AsyncMock, MagicMock

from agentic_rag.llm.lm_studio import LMStudioLLM


async def test_lm_studio_llm_returns_generated_text():
    llm = LMStudioLLM()

    message = MagicMock()
    message.content = "generated response"

    choice = MagicMock()
    choice.message = message

    response = MagicMock()
    response.choices = [choice]

    llm.client.chat.completions.create = AsyncMock(
        return_value=response,
    )

    result = await llm.generate("Hello")

    assert result == "generated response"

    llm.client.chat.completions.create.assert_awaited_once()


# async def test_lm_studio_real_call():
#     llm = LMStudioLLM()

#     result = await llm.generate(
#         "In one sentence, what is query decomposition?"
#     )

#     assert result
#     print(result)
