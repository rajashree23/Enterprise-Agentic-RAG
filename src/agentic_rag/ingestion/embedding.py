from __future__ import annotations

from collections.abc import Sequence
from typing import Any, Protocol


class EmbeddingModel(Protocol):
    @property
    def model_name(self) -> str: ...

    @property
    def max_tokens(self) -> int: ...

    @property
    def dimensions(self) -> int: ...

    def count(self, text: str) -> int: ...

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]: ...

    def embed_query(self, text: str) -> list[float]: ...


class EmbeddingInputError(ValueError):
    pass


class BgeSmallEmbeddingModel:
    """BGE Small v1.5 adapter for token counting and dense embeddings."""

    MODEL_NAME = "BAAI/bge-small-en-v1.5"
    QUERY_PREFIX = "Represent this sentence for searching relevant passages: "
    EXPECTED_MAX_TOKENS = 512
    EXPECTED_DIMENSIONS = 384

    def __init__(
        self,
        *,
        device: str | None = None,
        cache_folder: str | None = None,
        model: Any | None = None,
        batch_size: int = 8,
    ) -> None:
        if batch_size <= 0:
            raise ValueError("Embedding batch size must be positive")
        if model is None:
            # Keep this import local so normal application startup does not load
            # the comparatively heavy PyTorch/Transformers stack.
            from sentence_transformers import SentenceTransformer

            model = SentenceTransformer(
                self.MODEL_NAME,
                device=device,
                cache_folder=cache_folder,
            )

        self._model = model
        self._tokenizer = model.tokenizer
        self._batch_size = batch_size
        self._max_tokens = int(model.max_seq_length)
        dimension_getter = getattr(model, "get_embedding_dimension", None)
        self._dimensions = int(
            dimension_getter()
            if callable(dimension_getter)
            else model.get_sentence_embedding_dimension()
        )

        if self._max_tokens != self.EXPECTED_MAX_TOKENS:
            raise ValueError(
                f"Unexpected BGE token limit: {self._max_tokens}; "
                f"expected {self.EXPECTED_MAX_TOKENS}"
            )
        if self._dimensions != self.EXPECTED_DIMENSIONS:
            raise ValueError(
                f"Unexpected BGE embedding dimension: {self._dimensions}; "
                f"expected {self.EXPECTED_DIMENSIONS}"
            )

    @property
    def model_name(self) -> str:
        return self.MODEL_NAME

    @property
    def max_tokens(self) -> int:
        return self._max_tokens

    @property
    def dimensions(self) -> int:
        return self._dimensions

    def count(self, text: str) -> int:
        """Count the complete input without silently truncating it."""
        input_ids = self._tokenizer.encode(
            text,
            add_special_tokens=True,
            truncation=False,
            verbose=False,
        )
        return len(input_ids)

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []
        for text in texts:
            self._ensure_fits(text, input_kind="document")
        vectors = self._model.encode(
            list(texts),
            batch_size=self._batch_size,
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        return [vector.tolist() for vector in vectors]

    def embed_query(self, text: str) -> list[float]:
        query_input = f"{self.QUERY_PREFIX}{text}"
        self._ensure_fits(query_input, input_kind="query")
        vector = self._model.encode(
            query_input,
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        return vector.tolist()

    def _ensure_fits(self, text: str, *, input_kind: str) -> None:
        token_count = self.count(text)
        if token_count > self.max_tokens:
            raise EmbeddingInputError(
                f"BGE {input_kind} input has {token_count} tokens; "
                f"maximum is {self.max_tokens}"
            )


class PromptedSentenceTransformerEmbeddingModel:
    """Adapter for models that publish a Sentence Transformers query prompt."""

    MODEL_NAME = ""
    QUERY_PROMPT_NAME = "query"
    EXPECTED_DIMENSIONS = 0
    EXPECTED_MAX_TOKENS: int | None = None

    def __init__(
        self,
        *,
        device: str | None = None,
        cache_folder: str | None = None,
        model: Any | None = None,
        batch_size: int = 8,
    ) -> None:
        if batch_size <= 0:
            raise ValueError("Embedding batch size must be positive")
        if model is None:
            from sentence_transformers import SentenceTransformer

            model = SentenceTransformer(
                self.MODEL_NAME,
                device=device,
                cache_folder=cache_folder,
            )

        self._model = model
        self._tokenizer = model.tokenizer
        self._batch_size = batch_size
        self._max_tokens = int(model.max_seq_length)
        dimension_getter = getattr(model, "get_embedding_dimension", None)
        self._dimensions = int(
            dimension_getter()
            if callable(dimension_getter)
            else model.get_sentence_embedding_dimension()
        )
        prompts = getattr(model, "prompts", {})
        self._query_prefix = prompts.get(self.QUERY_PROMPT_NAME)
        if not isinstance(self._query_prefix, str) or not self._query_prefix:
            raise ValueError(
                f"{self.MODEL_NAME} does not define the expected query prompt"
            )
        if self._dimensions != self.EXPECTED_DIMENSIONS:
            raise ValueError(
                f"Unexpected {self.MODEL_NAME} embedding dimension: "
                f"{self._dimensions}; expected {self.EXPECTED_DIMENSIONS}"
            )
        if (
            self.EXPECTED_MAX_TOKENS is not None
            and self._max_tokens != self.EXPECTED_MAX_TOKENS
        ):
            raise ValueError(
                f"Unexpected {self.MODEL_NAME} token limit: {self._max_tokens}; "
                f"expected {self.EXPECTED_MAX_TOKENS}"
            )

    @property
    def model_name(self) -> str:
        return self.MODEL_NAME

    @property
    def max_tokens(self) -> int:
        return self._max_tokens

    @property
    def dimensions(self) -> int:
        return self._dimensions

    def count(self, text: str) -> int:
        input_ids = self._tokenizer.encode(
            text,
            add_special_tokens=True,
            truncation=False,
            verbose=False,
        )
        return len(input_ids)

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []
        for text in texts:
            self._ensure_fits(text, input_kind="document")
        vectors = self._model.encode(
            list(texts),
            batch_size=self._batch_size,
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        return [vector.tolist() for vector in vectors]

    def embed_query(self, text: str) -> list[float]:
        complete_input = f"{self._query_prefix}{text}"
        self._ensure_fits(complete_input, input_kind="query")
        vector = self._model.encode(
            text,
            prompt_name=self.QUERY_PROMPT_NAME,
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        return vector.tolist()

    def _ensure_fits(self, text: str, *, input_kind: str) -> None:
        token_count = self.count(text)
        if token_count > self.max_tokens:
            raise EmbeddingInputError(
                f"{self.MODEL_NAME} {input_kind} input has {token_count} tokens; "
                f"maximum is {self.max_tokens}"
            )


class QwenEmbeddingModel(PromptedSentenceTransformerEmbeddingModel):
    MODEL_NAME = "Qwen/Qwen3-Embedding-0.6B"
    EXPECTED_DIMENSIONS = 1024
    EXPECTED_MAX_TOKENS = 32768


class YuanEmbeddingModel(PromptedSentenceTransformerEmbeddingModel):
    MODEL_NAME = "IEITYuan/Yuan-embedding-2.0-en"
    EXPECTED_DIMENSIONS = 1024


class TransformersTokenCounter:
    """Tokenizer-only counter used to create a shared comparison corpus."""

    def __init__(self, model_name: str) -> None:
        from transformers import AutoTokenizer

        self._tokenizer = AutoTokenizer.from_pretrained(model_name)

    def count(self, text: str) -> int:
        return len(
            self._tokenizer.encode(
                text,
                add_special_tokens=True,
                truncation=False,
                verbose=False,
            )
        )
