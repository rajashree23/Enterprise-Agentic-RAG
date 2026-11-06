from __future__ import annotations

from pathlib import Path

from agentic_rag.ingestion.notion.chunking import ChunkRecord
from agentic_rag.ingestion.retrieval_evaluation import (
    EvaluationQuery,
    RankedChunk,
    RelevanceLabel,
    aggregate_metrics,
    calculate_query_metrics,
    load_evaluation_queries,
    rank_chunks,
    resolve_relevant_chunk_ids,
)

QUERIES_PATH = (
    Path(__file__).parents[1]
    / "docs/evaluations/offline-ingestion/notion-retrieval-queries.json"
)


def _chunk(chunk_id: str, document_id: str, content: str) -> ChunkRecord:
    return ChunkRecord(
        chunk_id=chunk_id,
        document_id=document_id,
        revision_id="revision",
        chunk_index=0,
        content=content,
        embedding_input=content,
        content_kind="prose",
        heading_path=("Decision",),
        block_ids=("block",),
        token_count=10,
        chunking_version="test",
        fragment_index=None,
        overlap_token_count=0,
    )


def test_resolves_text_labels_to_model_specific_chunks() -> None:
    chunks = (
        _chunk("relevant", "payment", "Payment Orchestrator owns\nthe workflow."),
        _chunk("other", "retry", "Retry connection failures."),
    )
    query = EvaluationQuery(
        query_id="owner",
        text="Who owns it?",
        relevant=(RelevanceLabel("Payment Architecture", "owns the workflow"),),
    )

    result = resolve_relevant_chunk_ids(
        query,
        chunks,
        {"payment": "Payment Architecture", "retry": "Retry Design"},
    )

    assert result == frozenset({"relevant"})


def test_ranks_normalized_vectors_by_dot_product() -> None:
    chunks = (
        _chunk("first", "doc", "First"),
        _chunk("second", "doc", "Second"),
    )

    ranked = rank_chunks(
        chunks,
        {"doc": "Document"},
        [[0.0, 1.0], [1.0, 0.0]],
        [1.0, 0.0],
        k=2,
    )

    assert [result.chunk.chunk_id for result in ranked] == ["second", "first"]
    assert ranked[0].score == 1.0


def test_calculates_and_aggregates_retrieval_metrics() -> None:
    ranked = (
        RankedChunk(_chunk("irrelevant", "doc", "A"), "Document", 0.9),
        RankedChunk(_chunk("relevant-1", "doc", "B"), "Document", 0.8),
        RankedChunk(_chunk("relevant-2", "doc", "C"), "Document", 0.7),
    )

    query = calculate_query_metrics(
        "query-1",
        ranked,
        frozenset({"relevant-1", "relevant-2"}),
    )
    summary = aggregate_metrics((query,), k=3)

    assert query.hit_rate == 1.0
    assert query.precision == 2 / 3
    assert query.recall == 1.0
    assert query.reciprocal_rank == 0.5
    assert 0.6 < query.ndcg < 1.0
    assert summary.hit_rate == 1.0
    assert summary.precision == 2 / 3
    assert summary.mrr == 0.5


def test_notion_evaluation_queries_mix_single_and_multi_evidence() -> None:
    queries = load_evaluation_queries(QUERIES_PATH)

    label_counts = [len(query.relevant) for query in queries]
    assert len(queries) == 15
    assert min(label_counts) == 1
    assert max(label_counts) >= 3
