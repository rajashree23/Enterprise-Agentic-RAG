from __future__ import annotations

import math

from agentic_rag.ingestion.embedding import BgeSmallEmbeddingModel


def main() -> None:
    print(f"Loading {BgeSmallEmbeddingModel.MODEL_NAME}...")
    model = BgeSmallEmbeddingModel()

    query = "Which component owns the payment workflow?"
    passages = [
        "The Payment Orchestrator owns the payment workflow.",
        "Payment credentials are stored in the secrets manager.",
    ]
    query_vector = model.embed_query(query)
    passage_vectors = model.embed_documents(passages)

    print(f"Model: {model.model_name}")
    print(f"Maximum tokens: {model.max_tokens}")
    print(f"Embedding dimensions: {model.dimensions}")
    print(
        f"Query tokens (including instruction): {model.count(model.QUERY_PREFIX + query)}"
    )
    print("Sample ranking:")
    ranked = sorted(
        (
            (_cosine_similarity(query_vector, vector), passage)
            for passage, vector in zip(passages, passage_vectors, strict=True)
        ),
        reverse=True,
    )
    for rank, (score, passage) in enumerate(ranked, start=1):
        print(f"  {rank}. {score:.4f} | {passage}")


def _cosine_similarity(left: list[float], right: list[float]) -> float:
    dot_product = sum(a * b for a, b in zip(left, right, strict=True))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return dot_product / (left_norm * right_norm)


if __name__ == "__main__":
    main()
