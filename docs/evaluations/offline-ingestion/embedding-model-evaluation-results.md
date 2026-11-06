# Notion embedding-model evaluation results

## Status

Preliminary local evaluation completed on 2026-11-04. These results identify a
current leader but do not yet make the production model decision.

## Evaluation setup

| Setting | Value |
| --- | --- |
| Source corpus | Four live Notion architecture and design pages |
| Common chunks | 19 chunks produced with the BGE tokenizer |
| Chunk ceiling | 512 BGE tokens, including special tokens, title, heading context, and content |
| Oversized overlap | 32 tokens; an initial bounded-overlap heuristic |
| Fragment chunks | 3 |
| Labelled queries | 15: 5 single-fact and 10 multi-evidence queries |
| Relevant chunks per query | Minimum 1, maximum 4, mean 2.67 |
| Retrieval depth | `k = 5` |
| Search | Normalized dense vectors with dot product, equivalent to cosine similarity |
| Embedding batch size | 8 |
| Runtime | NVIDIA GeForce RTX 5050 Laptop GPU through PyTorch CUDA 13.0 |

The evaluator rejects a query only when it resolves to no relevant chunks. A
dataset regression test ensures that both single-fact and multi-evidence
queries remain represented. The multi-evidence portion prevents aggregate
Recall@k from collapsing into the same binary signal as Hit Rate@k.

### How relevant chunks are defined

Each query contains multiple manually selected evidence labels. A label names
the expected page and a stable text anchor. The evaluator maps every label to
the common generated chunks, removes duplicate chunk IDs, and uses the size of
that set as the recall denominator.

For example, if a query has four relevant chunks and retrieves three in the top
five:

```text
Hit Rate@5  = 1
Precision@5 = 3 / 5 = 0.60
Recall@5    = 3 / 4 = 0.75
```

The same chunk text, labels, queries, `k`, batch size, and ranking implementation
were used for every model. Query prompts came from each model's documented
configuration; documents were embedded without a query prompt. Silent input
truncation was disabled.

### Why the common ceiling is 512 BGE tokens

BGE has the smallest input limit in the shortlist: 512 tokens. A fair model
comparison requires every model to embed the same chunk text. If Qwen or Yuan
used their much larger limits to create larger chunks, BGE would have to split
those chunks and the models would no longer solve the same retrieval problem.

The ceiling covers the complete document embedding input. It is an upper bound,
not a target; the largest chunk in this run contained 508 BGE tokens.

### Why the oversized overlap is 32 tokens

The 32-token overlap is a first-iteration heuristic equal to 6.25% of BGE's
512-token limit. When one source block must be split, the chunker reserves up
to 32 tokens for a suffix from the preceding fragment. Ordinary chunks and
tables do not receive this generic overlap.

This value is not yet optimized. A later chunking evaluation should compare
values such as 0, 16, 32, and 64 and select the smallest overlap that improves
retrieval.

## Retrieval quality

| Model | Hit Rate@5 | Precision@5 | Recall@5 | MRR@5 | nDCG@5 |
| --- | ---: | ---: | ---: | ---: | ---: |
| `BAAI/bge-small-en-v1.5` | 0.9333 | 0.4267 | 0.8667 | 0.7889 | 0.7798 |
| `Qwen/Qwen3-Embedding-0.6B` | **1.0000** | **0.4800** | **0.9333** | **0.9222** | **0.8783** |
| `IEITYuan/Yuan-embedding-2.0-en` | **1.0000** | 0.4533 | 0.9000 | 0.8889 | 0.8376 |

The metrics measure different behavior. BGE found at least one relevant chunk
for 93.33% of queries but retrieved 86.67% of the expected evidence on average.
Qwen found relevant evidence for every query and achieved 93.33% average recall.

## Recall@5 by query

| Query | Relevant chunks | BGE | Qwen | Yuan |
| --- | ---: | ---: | ---: | ---: |
| Payment Orchestrator responsibilities | 3 | 1.00 | 1.00 | 1.00 |
| Provider interaction controls | 4 | 0.75 | 0.75 | 1.00 |
| Payment security and reliability | 4 | 0.00 | 0.75 | 0.50 |
| Idempotency lifecycle | 4 | 0.75 | 0.75 | 0.75 |
| Payment ownership and escalation | 4 | 0.75 | 0.75 | 0.75 |
| Cross-system retry handling | 4 | 0.75 | 1.00 | 0.50 |
| Ingestion content integrity | 3 | 1.00 | 1.00 | 1.00 |
| Citation and authorization | 3 | 1.00 | 1.00 | 1.00 |
| Revision publication and cleanup | 3 | 1.00 | 1.00 | 1.00 |
| Chunking and embedding pipeline | 3 | 1.00 | 1.00 | 1.00 |
| Payment availability target | 1 | 1.00 | 1.00 | 1.00 |
| Idempotency retention | 1 | 1.00 | 1.00 | 1.00 |
| Fraud Service owner | 1 | 1.00 | 1.00 | 1.00 |
| Ledger escalation | 1 | 1.00 | 1.00 | 1.00 |
| Table-header rule | 1 | 1.00 | 1.00 | 1.00 |

The payment-security query is the clearest differentiator: BGE retrieved none
of its four labelled control chunks in the top five, Qwen retrieved three, and
Yuan retrieved two. The cross-system retry query also favors Qwen.

## Operational results on CUDA

| Model | Cached load | Embed/index 19 chunks | Mean query | p50 query | p95 query | Peak process RAM | Peak CUDA memory | Raw vectors |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| BGE Small | **9.668 s** | **0.332 s** | **8.7 ms** | **6.8 ms** | **15.7 ms** | **1,377.95 MiB** | **227.22 MiB** | **0.03 MiB** |
| Qwen3 0.6B | 12.816 s | 0.731 s | 39.3 ms | 34.9 ms | 57.0 ms | 2,040.62 MiB | 1,267.76 MiB | 0.07 MiB |
| Yuan 2.0 EN | 12.530 s | 0.632 s | 39.0 ms | 33.4 ms | 59.8 ms | 2,040.26 MiB | 1,267.76 MiB | 0.07 MiB |

Query latency includes query embedding and in-memory ranking over 19 vectors.
It excludes Notion acquisition and rendering. Embed/index time excludes
persistent vector-database insertion.

Model-load and latency values come from one cached run per model and can vary
because of operating-system scheduling, model-cache checks, and GPU warm-up.
They are useful directional measurements, not stable production percentiles.
The p95 value is especially weak with only ten queries; repeated warm runs are
required before using it for a service-level objective.

Raw vector storage assumes float32 values and excludes vector-index, metadata,
and chunk-text overhead.

### Why the evaluation uses a GPU

GPU access is provided by the CUDA-enabled PyTorch package. Sentence
Transformers uses PyTorch to place the embedding model's weights and input
tensors in GPU memory and execute the model's attention, matrix operations,
pooling, and vector normalization on the NVIDIA GPU. The resulting vectors are
then copied back to CPU memory for this evaluator.

Not every part of the flow runs on the GPU. Notion API calls, tokenization,
normalization, chunking, relevance-label resolution, and the current Python
dot-product ranking remain on the CPU. Only embedding-model inference is
offloaded.

The GPU was selected because embedding inference consists mostly of highly
parallel matrix operations, which GPUs execute faster than a general-purpose
CPU. All three shortlisted models fit comfortably within the development
GPU's 8 GiB VRAM, so GPU execution shortens the evaluation cycle and represents
the intended local deployment option. GPU RAM and normal process RAM remain
separate resources and are therefore reported in separate columns.

## Input compatibility

| Model | Runtime input limit | Largest common chunk in model tokens | Result |
| --- | ---: | ---: | --- |
| BGE Small | 512 | 508 | Pass |
| Qwen3 0.6B | 32,768 | 458 | Pass |
| Yuan 2.0 EN | 32,768 | 458 | Pass |

The loaded Yuan model reported a 32,768-token runtime limit, while the MTEB
shortlist metadata recorded 2,048. The difference did not affect this test
because the common corpus is capped at 512 BGE tokens. A production decision
must pin and verify the selected model revision.

## Preliminary interpretation

Qwen is the current retrieval-quality leader. It achieved the highest value on
every aggregate retrieval metric and used about 1.27 GiB of CUDA memory, well
within the development GPU's 8 GiB capacity.

Yuan ranked second overall. It retrieved all evidence for the provider-control
query but underperformed Qwen on payment security and cross-system retry
handling. Its runtime footprint was similar to Qwen in this setup.

BGE remains the efficiency option. It was much faster and used substantially
less CUDA memory, but it missed all labelled evidence for one multi-evidence
query and had the lowest aggregate recall and ranking quality.

The current evidence supports carrying Qwen forward as the quality candidate
and BGE as the efficiency fallback. A final choice still requires human review
of the multi-evidence labels, more documents and query phrasings, repeated
timing runs, and evaluation with the eventual vector-store implementation.

## Reproduction

Activate the `agentic-rag` Conda environment, load the Notion environment
variables, and select one model:

```bat
for /f "usebackq tokens=1,* delims==" %A in (".env") do @set "%A=%B"
set PYTHONPATH=%CD%\src
set EMBEDDING_MODEL=qwen
python -m agentic_rag.ingestion.evaluate_embedding_retrieval
```

Use `bge`, `qwen`, or `yuan`. Confirm CUDA before comparing GPU timings:

```bat
python -c "import torch; print(torch.cuda.is_available(), torch.cuda.get_device_name(0))"
```
