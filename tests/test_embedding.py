from __future__ import annotations

import pytest

from agentic_rag.ingestion.embedding import (
    BgeSmallEmbeddingModel,
    QwenEmbeddingModel,
)


class _FakeTokenizer:
    def encode(
        self,
        text: str,
        *,
        add_special_tokens: bool,
        truncation: bool,
        verbose: bool,
    ) -> list[int]:
        assert add_special_tokens is True
        assert truncation is False
        assert verbose is False
        return [101, *(range(len(text.split()))), 102]


class _Vector(list[float]):
    def tolist(self) -> list[float]:
        return list(self)


class _FakeModel:
    tokenizer = _FakeTokenizer()
    max_seq_length = 512

    def get_sentence_embedding_dimension(self) -> int:
        return 384

    def encode(
        self,
        texts: str | list[str],
        *,
        batch_size: int | None = None,
        normalize_embeddings: bool,
        convert_to_numpy: bool,
        show_progress_bar: bool,
    ) -> _Vector | list[_Vector]:
        assert normalize_embeddings is True
        assert convert_to_numpy is True
        assert show_progress_bar is False
        if isinstance(texts, list):
            assert batch_size == 8
        if isinstance(texts, str):
            return _Vector([1.0, 0.0])
        return [_Vector([float(index), 1.0]) for index, _ in enumerate(texts)]


def test_bge_counter_uses_special_tokens_without_truncation() -> None:
    model = BgeSmallEmbeddingModel(model=_FakeModel())

    assert model.count("one two three") == 5
    assert model.max_tokens == 512
    assert model.dimensions == 384


def test_bge_uses_query_instruction_only_for_queries() -> None:
    fake = _RecordingModel()
    model = BgeSmallEmbeddingModel(model=fake)

    model.embed_query("payment owner")
    model.embed_documents(["payment document"])

    assert fake.inputs[0] == (
        "Represent this sentence for searching relevant passages: payment owner"
    )
    assert fake.inputs[1] == ["payment document"]


class _RecordingModel(_FakeModel):
    def __init__(self) -> None:
        self.inputs: list[str | list[str]] = []

    def encode(
        self,
        texts: str | list[str],
        *,
        batch_size: int | None = None,
        normalize_embeddings: bool,
        convert_to_numpy: bool,
        show_progress_bar: bool,
    ) -> _Vector | list[_Vector]:
        self.inputs.append(texts)
        return super().encode(
            texts,
            batch_size=batch_size,
            normalize_embeddings=normalize_embeddings,
            convert_to_numpy=convert_to_numpy,
            show_progress_bar=show_progress_bar,
        )


def test_bge_rejects_unexpected_model_contract() -> None:
    fake = _FakeModel()
    fake.max_seq_length = 256

    with pytest.raises(ValueError, match="Unexpected BGE token limit"):
        BgeSmallEmbeddingModel(model=fake)


class _PromptedFakeModel(_FakeModel):
    max_seq_length = 32768

    def __init__(self) -> None:
        self.prompts = {
            "query": (
                "Instruct: Given a web search query, retrieve relevant passages "
                "that answer the query\nQuery:"
            )
        }
        self.inputs: list[tuple[str | list[str], str | None]] = []

    def get_sentence_embedding_dimension(self) -> int:
        return 1024

    def encode(
        self,
        texts: str | list[str],
        *,
        batch_size: int | None = None,
        prompt_name: str | None = None,
        normalize_embeddings: bool,
        convert_to_numpy: bool,
        show_progress_bar: bool,
    ) -> _Vector | list[_Vector]:
        self.inputs.append((texts, prompt_name))
        return super().encode(
            texts,
            batch_size=batch_size,
            normalize_embeddings=normalize_embeddings,
            convert_to_numpy=convert_to_numpy,
            show_progress_bar=show_progress_bar,
        )


def test_qwen_uses_published_query_prompt() -> None:
    fake = _PromptedFakeModel()
    model = QwenEmbeddingModel(model=fake)

    model.embed_query("payment owner")
    model.embed_documents(["payment document"])

    assert fake.inputs == [
        ("payment owner", "query"),
        (["payment document"], None),
    ]
