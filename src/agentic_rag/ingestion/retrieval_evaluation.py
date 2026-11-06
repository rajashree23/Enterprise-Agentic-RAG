from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from agentic_rag.ingestion.notion.chunking import ChunkRecord


@dataclass(frozen=True, slots=True)
class RelevanceLabel:
    page_title: str
    text_anchor: str


@dataclass(frozen=True, slots=True)
class EvaluationQuery:
    query_id: str
    text: str
    relevant: tuple[RelevanceLabel, ...]


@dataclass(frozen=True, slots=True)
class RankedChunk:
    chunk: ChunkRecord
    page_title: str
    score: float


@dataclass(frozen=True, slots=True)
class QueryMetrics:
    query_id: str
    hit_rate: float
    precision: float
    recall: float
    reciprocal_rank: float
    ndcg: float
    relevant_chunk_count: int
    relevant_chunk_ids: frozenset[str]
    ranked: tuple[RankedChunk, ...]


@dataclass(frozen=True, slots=True)
class EvaluationMetrics:
    query_count: int
    k: int
    hit_rate: float
    precision: float
    recall: float
    mrr: float
    ndcg: float
    queries: tuple[QueryMetrics, ...]


def load_evaluation_queries(path: Path) -> tuple[EvaluationQuery, ...]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list) or not payload:
        raise ValueError("Evaluation query file must contain a non-empty list")

    queries = tuple(_parse_query(item) for item in payload)
    query_ids = [query.query_id for query in queries]
    if len(query_ids) != len(set(query_ids)):
        raise ValueError("Evaluation query IDs must be unique")
    return queries


def resolve_relevant_chunk_ids(
    query: EvaluationQuery,
    chunks: tuple[ChunkRecord, ...],
    page_titles_by_document_id: dict[str, str],
) -> frozenset[str]:
    relevant_ids: set[str] = set()
    for label in query.relevant:
        normalized_anchor = _normalized_text(label.text_anchor)
        matches = [
            chunk.chunk_id
            for chunk in chunks
            if page_titles_by_document_id.get(chunk.document_id) == label.page_title
            and normalized_anchor in _normalized_text(chunk.content)
        ]
        if not matches:
            raise ValueError(
                f"Query {query.query_id!r} label did not resolve: "
                f"{label.page_title!r} / {label.text_anchor!r}"
            )
        relevant_ids.update(matches)
    return frozenset(relevant_ids)


def rank_chunks(
    chunks: tuple[ChunkRecord, ...],
    page_titles_by_document_id: dict[str, str],
    chunk_vectors: list[list[float]],
    query_vector: list[float],
    *,
    k: int,
) -> tuple[RankedChunk, ...]:
    if k <= 0:
        raise ValueError("k must be positive")
    if len(chunks) != len(chunk_vectors):
        raise ValueError("Every chunk must have exactly one vector")

    ranked = sorted(
        (
            RankedChunk(
                chunk=chunk,
                page_title=page_titles_by_document_id[chunk.document_id],
                score=_dot_product(query_vector, vector),
            )
            for chunk, vector in zip(chunks, chunk_vectors, strict=True)
        ),
        key=lambda result: result.score,
        reverse=True,
    )
    return tuple(ranked[:k])


def calculate_query_metrics(
    query_id: str,
    ranked: tuple[RankedChunk, ...],
    relevant_chunk_ids: frozenset[str],
) -> QueryMetrics:
    if not relevant_chunk_ids:
        raise ValueError("At least one relevant chunk is required")

    relevance = [result.chunk.chunk_id in relevant_chunk_ids for result in ranked]
    relevant_found = sum(relevance)
    first_relevant_rank = next(
        (rank for rank, is_relevant in enumerate(relevance, start=1) if is_relevant),
        None,
    )
    dcg = sum(
        1.0 / math.log2(rank + 1)
        for rank, is_relevant in enumerate(relevance, start=1)
        if is_relevant
    )
    ideal_count = min(len(relevant_chunk_ids), len(ranked))
    ideal_dcg = sum(1.0 / math.log2(rank + 1) for rank in range(1, ideal_count + 1))

    return QueryMetrics(
        query_id=query_id,
        hit_rate=1.0 if relevant_found else 0.0,
        precision=relevant_found / len(ranked) if ranked else 0.0,
        recall=relevant_found / len(relevant_chunk_ids),
        reciprocal_rank=(1.0 / first_relevant_rank if first_relevant_rank else 0.0),
        ndcg=(dcg / ideal_dcg if ideal_dcg else 0.0),
        relevant_chunk_count=len(relevant_chunk_ids),
        relevant_chunk_ids=relevant_chunk_ids,
        ranked=ranked,
    )


def aggregate_metrics(
    query_metrics: tuple[QueryMetrics, ...],
    *,
    k: int,
) -> EvaluationMetrics:
    if not query_metrics:
        raise ValueError("At least one evaluated query is required")
    count = len(query_metrics)
    return EvaluationMetrics(
        query_count=count,
        k=k,
        hit_rate=sum(item.hit_rate for item in query_metrics) / count,
        precision=sum(item.precision for item in query_metrics) / count,
        recall=sum(item.recall for item in query_metrics) / count,
        mrr=sum(item.reciprocal_rank for item in query_metrics) / count,
        ndcg=sum(item.ndcg for item in query_metrics) / count,
        queries=query_metrics,
    )


def _parse_query(value: Any) -> EvaluationQuery:
    if not isinstance(value, dict):
        raise TypeError("Each evaluation query must be an object")
    query_id = _required_string(value, "id")
    text = _required_string(value, "query")
    raw_labels = value.get("relevant")
    if not isinstance(raw_labels, list) or not raw_labels:
        raise ValueError(f"Query {query_id!r} must have relevance labels")
    labels = tuple(
        RelevanceLabel(
            page_title=_required_string(label, "page_title"),
            text_anchor=_required_string(label, "text_anchor"),
        )
        for label in raw_labels
        if isinstance(label, dict)
    )
    if len(labels) != len(raw_labels):
        raise TypeError(f"Query {query_id!r} has a non-object relevance label")
    return EvaluationQuery(query_id=query_id, text=text, relevant=labels)


def _required_string(value: dict[str, Any], key: str) -> str:
    result = value.get(key)
    if not isinstance(result, str) or not result.strip():
        raise ValueError(f"Evaluation field {key!r} must be a non-empty string")
    return result.strip()


def _dot_product(left: list[float], right: list[float]) -> float:
    if len(left) != len(right):
        raise ValueError("Query and chunk vector dimensions must match")
    return sum(a * b for a, b in zip(left, right, strict=True))


def _normalized_text(value: str) -> str:
    return " ".join(value.casefold().split())
