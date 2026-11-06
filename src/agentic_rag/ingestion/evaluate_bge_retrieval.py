from __future__ import annotations

import asyncio
import os
import statistics
import sys
import time
from pathlib import Path

from agentic_rag.ingestion.embedding import (
    BgeSmallEmbeddingModel,
    QwenEmbeddingModel,
    TransformersTokenCounter,
    YuanEmbeddingModel,
)
from agentic_rag.ingestion.notion import (
    ChunkingConfig,
    ChunkRecord,
    NotionChunker,
    NotionClient,
    NotionPageAcquirer,
    NotionPageNormalizer,
    PageSnapshot,
)
from agentic_rag.ingestion.retrieval_evaluation import (
    aggregate_metrics,
    calculate_query_metrics,
    load_evaluation_queries,
    rank_chunks,
    resolve_relevant_chunk_ids,
)

DEFAULT_QUERIES_PATH = Path(
    "docs/evaluations/offline-ingestion/notion-retrieval-queries.json"
)
MODEL_FACTORIES = {
    "bge": BgeSmallEmbeddingModel,
    "qwen": QwenEmbeddingModel,
    "yuan": YuanEmbeddingModel,
}
COMMON_CHUNK_MAX_TOKENS = 512


def _required_environment(name: str) -> str:
    value = os.environ.get(name)
    if value is None or not value.strip():
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value.strip()


def _raw_page_title(page: PageSnapshot) -> str:
    properties = page.value.get("properties")
    if not isinstance(properties, dict):
        return "<unknown>"
    for value in properties.values():
        if not isinstance(value, dict) or not isinstance(value.get("title"), list):
            continue
        return "".join(
            item.get("plain_text", "")
            for item in value["title"]
            if isinstance(item, dict) and isinstance(item.get("plain_text"), str)
        )
    return "<unknown>"


async def main() -> None:
    api_key = _required_environment("NOTION_API_KEY")
    root_page_id = _required_environment("NOTION_ROOT_PAGE_ID")
    api_version = os.environ.get("NOTION_API_VERSION", "2026-03-11")
    connection_id = os.environ.get("NOTION_CONNECTION_ID", "local-evaluation")
    queries_path = Path(os.environ.get("RETRIEVAL_QUERIES", DEFAULT_QUERIES_PATH))
    k = int(os.environ.get("RETRIEVAL_K", "5"))
    overlap_tokens = int(os.environ.get("CHUNK_OVERLAP_TOKENS", "32"))
    batch_size = int(os.environ.get("EMBEDDING_BATCH_SIZE", "8"))
    minimum_relevant_chunks = int(os.environ.get("MIN_RELEVANT_CHUNKS", "1"))
    model_key = os.environ.get("EMBEDDING_MODEL", "qwen").strip().casefold()
    try:
        model_factory = MODEL_FACTORIES[model_key]
    except KeyError as error:
        supported = ", ".join(MODEL_FACTORIES)
        raise ValueError(
            f"Unsupported EMBEDDING_MODEL {model_key!r}; choose {supported}"
        ) from error

    model_load_started = time.perf_counter()
    model = model_factory(batch_size=batch_size)
    model_load_seconds = time.perf_counter() - model_load_started
    _reset_cuda_peak_memory()
    queries = load_evaluation_queries(queries_path)

    acquisition_started = time.perf_counter()
    async with NotionClient(api_key, api_version=api_version) as client:
        pages = await NotionPageAcquirer(client).fetch_descendants(root_page_id)
    acquisition_seconds = time.perf_counter() - acquisition_started

    preparation_started = time.perf_counter()
    titles = {page.page_id: _raw_page_title(page) for page in pages}
    normalizer = NotionPageNormalizer(connection_id)
    common_token_counter = TransformersTokenCounter(BgeSmallEmbeddingModel.MODEL_NAME)
    chunker = NotionChunker(
        common_token_counter,
        ChunkingConfig(
            max_tokens=COMMON_CHUNK_MAX_TOKENS,
            overlap_tokens=overlap_tokens,
            chunking_version="notion-structure-common-512-v1",
        ),
    )

    documents = tuple(
        document
        for page in pages
        if (document := normalizer.normalize(page, page_titles_by_id=titles))
        is not None
    )
    chunks: tuple[ChunkRecord, ...] = tuple(
        chunk for document in documents for chunk in chunker.chunk(document)
    )
    page_titles_by_document_id = {
        document.record.document_id: document.record.page_title
        for document in documents
    }
    relevant_ids_by_query = {
        query.query_id: resolve_relevant_chunk_ids(
            query,
            chunks,
            page_titles_by_document_id,
        )
        for query in queries
    }
    insufficient = {
        query_id: len(relevant_ids)
        for query_id, relevant_ids in relevant_ids_by_query.items()
        if len(relevant_ids) < minimum_relevant_chunks
    }
    if insufficient:
        raise ValueError(
            f"Queries resolved to fewer than {minimum_relevant_chunks} "
            f"relevant chunks: {insufficient}"
        )
    preparation_seconds = time.perf_counter() - preparation_started

    indexing_started = time.perf_counter()
    chunk_vectors = model.embed_documents([chunk.embedding_input for chunk in chunks])
    indexing_seconds = time.perf_counter() - indexing_started

    results = []
    query_latencies: list[float] = []
    for query in queries:
        relevant_ids = relevant_ids_by_query[query.query_id]
        query_started = time.perf_counter()
        query_vector = model.embed_query(query.text)
        ranked = rank_chunks(
            chunks,
            page_titles_by_document_id,
            chunk_vectors,
            query_vector,
            k=k,
        )
        query_latencies.append(time.perf_counter() - query_started)
        results.append(calculate_query_metrics(query.query_id, ranked, relevant_ids))

    summary = aggregate_metrics(tuple(results), k=k)
    raw_vector_bytes = sum(len(vector) * 4 for vector in chunk_vectors)
    candidate_token_counts = [model.count(chunk.embedding_input) for chunk in chunks]
    max_chunk_tokens = max(candidate_token_counts, default=0)
    fragment_chunks = sum(chunk.fragment_index is not None for chunk in chunks)
    peak_process_bytes = _peak_process_memory_bytes()
    peak_cuda_bytes = _peak_cuda_memory_bytes()

    print(f"Model: {model.model_name}")
    print(f"Embedding dimensions: {model.dimensions}")
    print(f"Model input limit: {model.max_tokens}")
    print(
        f"Common chunk corpus: BGE tokenizer; "
        f"{COMMON_CHUNK_MAX_TOKENS}-token ceiling; overlap={overlap_tokens}"
    )
    print(f"Documents: {len(documents)}; chunks: {len(chunks)}")
    print(f"Queries: {summary.query_count}; k: {summary.k}")
    relevant_counts = [len(ids) for ids in relevant_ids_by_query.values()]
    print(
        "Relevant chunks per query: "
        f"min={min(relevant_counts)}; max={max(relevant_counts)}; "
        f"mean={statistics.mean(relevant_counts):.2f}"
    )
    print(f"Model load time: {model_load_seconds:.3f}s")
    print(f"Notion acquisition time: {acquisition_seconds:.3f}s")
    print(f"Normalization and chunking time: {preparation_seconds:.3f}s")
    print(f"Embedding/indexing time: {indexing_seconds:.3f}s")
    print(f"Mean query latency: {statistics.mean(query_latencies):.4f}s")
    print(f"p50 query latency: {statistics.median(query_latencies):.4f}s")
    print(f"p95 query latency: {_percentile(query_latencies, 0.95):.4f}s")
    print(f"Peak process memory: {_format_bytes(peak_process_bytes)}")
    if peak_cuda_bytes is not None:
        print(f"Peak CUDA memory: {_format_bytes(peak_cuda_bytes)}")
    print(f"Raw float32 vector storage: {_format_bytes(raw_vector_bytes)}")
    print(
        f"Input-limit compatibility: pass; max chunk={max_chunk_tokens}/"
        f"{model.max_tokens} tokens; fragment chunks={fragment_chunks}"
    )
    print(f"Hit Rate@{k}: {summary.hit_rate:.4f}")
    print(f"Precision@{k}: {summary.precision:.4f}")
    print(f"Recall@{k}: {summary.recall:.4f}")
    print(f"MRR@{k}: {summary.mrr:.4f}")
    print(f"nDCG@{k}: {summary.ndcg:.4f}")

    for result in summary.queries:
        print(
            f"\n{result.query_id}: hit={result.hit_rate:.0f}; "
            f"precision={result.precision:.3f}; recall={result.recall:.3f}; "
            f"rr={result.reciprocal_rank:.3f}; ndcg={result.ndcg:.3f}"
        )
        for rank, item in enumerate(result.ranked, start=1):
            relevant = "*" if item.chunk.chunk_id in result.relevant_chunk_ids else " "
            section = " > ".join(item.chunk.heading_path) or "<root>"
            print(
                f"  {relevant}{rank}. {item.score:.4f} | {item.page_title} | {section}"
            )


def _percentile(values: list[float], quantile: float) -> float:
    if not values:
        raise ValueError("Cannot calculate a percentile without values")
    if not 0 <= quantile <= 1:
        raise ValueError("Quantile must be between zero and one")
    ordered = sorted(values)
    index = (len(ordered) - 1) * quantile
    lower = int(index)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = index - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * fraction


def _peak_process_memory_bytes() -> int | None:
    if os.name == "nt":
        return _windows_peak_working_set_bytes()

    try:
        import resource
    except ImportError:
        return None
    peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return int(peak if sys.platform == "darwin" else peak * 1024)


def _windows_peak_working_set_bytes() -> int | None:
    import ctypes
    from ctypes import wintypes

    class ProcessMemoryCounters(ctypes.Structure):
        _fields_ = [
            ("cb", wintypes.DWORD),
            ("page_fault_count", wintypes.DWORD),
            ("peak_working_set_size", ctypes.c_size_t),
            ("working_set_size", ctypes.c_size_t),
            ("quota_peak_paged_pool_usage", ctypes.c_size_t),
            ("quota_paged_pool_usage", ctypes.c_size_t),
            ("quota_peak_non_paged_pool_usage", ctypes.c_size_t),
            ("quota_non_paged_pool_usage", ctypes.c_size_t),
            ("pagefile_usage", ctypes.c_size_t),
            ("peak_pagefile_usage", ctypes.c_size_t),
        ]

    counters = ProcessMemoryCounters()
    counters.cb = ctypes.sizeof(counters)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    psapi = ctypes.WinDLL("psapi", use_last_error=True)
    kernel32.GetCurrentProcess.restype = wintypes.HANDLE
    psapi.GetProcessMemoryInfo.argtypes = (
        wintypes.HANDLE,
        ctypes.POINTER(ProcessMemoryCounters),
        wintypes.DWORD,
    )
    psapi.GetProcessMemoryInfo.restype = wintypes.BOOL
    process = kernel32.GetCurrentProcess()
    success = psapi.GetProcessMemoryInfo(
        process,
        ctypes.byref(counters),
        counters.cb,
    )
    return int(counters.peak_working_set_size) if success else None


def _reset_cuda_peak_memory() -> None:
    try:
        import torch
    except ImportError:
        return
    if torch.cuda.is_available():
        torch.cuda.reset_peak_memory_stats()


def _peak_cuda_memory_bytes() -> int | None:
    try:
        import torch
    except ImportError:
        return None
    return int(torch.cuda.max_memory_allocated()) if torch.cuda.is_available() else None


def _format_bytes(value: int | None) -> str:
    if value is None:
        return "unavailable"
    mebibytes = value / (1024 * 1024)
    return f"{mebibytes:.2f} MiB"


if __name__ == "__main__":
    asyncio.run(main())
