# Notion embedding-model shortlist

## Status

Shortlist defined; final model selection pending local retrieval evaluation.

## Purpose

This document records how embedding models were shortlisted for the first
Notion offline-ingestion implementation. The shortlist is based on public MTEB
retrieval results and deployment characteristics. It does not select the final
model.

The final decision will be based on retrieval quality over representative
Notion architecture and design documents, together with deployment cost and
operational complexity.

## Why MTEB was used

MTEB provides comparable evaluation results for embedding models across
retrieval and other embedding tasks. The overall MTEB average was not used
because this system needs embeddings primarily for document retrieval.

The shortlist used the **MTEB English, version 2** benchmark and its
**Retrieval** score. The score is useful for narrowing the field, but it cannot
replace an evaluation using this system's own documents and queries.

## Leaderboard filters

The following leaderboard view was used:

```text
Benchmark: MTEB(eng, v2)
Task type: Retrieval
Modality: text
Model type: dense
Sentence Transformers compatible: yes
Experimental results: excluded
Required openness: open weights and open license
```

These selections correspond to this leaderboard URL:

<https://leaderboard.mteb.org/benchmark/MTEB(eng%2C%20v2)?types=Retrieval&mmods=text&st=1&noexp=1&openreq=weights%2Clicense&mtypes=dense>

| Selection | Meaning | Reason |
| --- | --- | --- |
| `MTEB(eng, v2)` | Uses the second version of the English MTEB benchmark. | The first supported Notion corpus is expected to contain English architecture and design documents. |
| Task type: `Retrieval` | Shows performance for retrieving relevant passages for a query. | Retrieval is the embedding model's job in the initial RAG flow. Classification, clustering, and other task scores should not determine this choice. |
| Modality: `text` | Includes models whose input is text. | The current Notion scope excludes images, audio, video, and other media. |
| Model type: `dense` | Includes models that produce one dense vector per query or chunk. | A dense-vector baseline is straightforward to store and search in a vector database. Sparse, multi-vector, late-interaction, hybrid, and reranking approaches are deferred until the baseline is evaluated. |
| Sentence Transformers compatible | Includes models loadable through the common Sentence Transformers interface. | This reduces initial integration effort and makes it easier to run the same evaluation pipeline for every candidate. |
| No experimental results | Excludes experimental variants from the displayed results. | The shortlist favors reproducible model entries over temporary or experimental configurations. |
| Open weights | Requires downloadable model weights. | The model must be deployable in an environment we control rather than being tied to one hosted API. |
| Open license | Requires a stated open license. | The model must be legally reviewable for deployment and redistribution within the intended system. License approval is still required before production use. |

The filters narrow the leaderboard; they do not prove that every remaining
model is operationally suitable. Model cards must still be checked for input
format, query instructions, dependencies, license terms, and deployment
requirements.

## Why three candidates were selected

Three candidates provide a small but useful quality-versus-cost comparison:

1. a small, inexpensive deployment baseline;
2. a modern and well-supported balanced candidate; and
3. a retrieval-quality candidate from the top of the filtered leaderboard.

Testing more models would increase download, integration, and evaluation time
without first establishing whether the additional choices improve retrieval on
our Notion corpus. Testing fewer models would not expose the trade-off between
deployment cost and retrieval quality.

Large 4B, 7B, and 8B models were not shortlisted for the first iteration. Their
additional compute and memory cost is difficult to justify before the 33M and
596M candidates have been tested on the target corpus.

## Shortlisted models

The following values were recorded from the filtered MTEB leaderboard and its
model pages on 2026-10-29.

| Role | Model | Parameters | Memory shown by MTEB | Embedding dimensions | Maximum tokens | MTEB English-v2 retrieval | License |
| --- | --- | ---: | ---: | ---: | ---: | ---: | --- |
| Low-cost baseline | `BAAI/bge-small-en-v1.5` | 33M | 127 MB | 384 | 512 | 53.86 | MIT |
| Balanced candidate | `Qwen/Qwen3-Embedding-0.6B` | 596M | 1.1 GB | up to 1,024 | 32,768 | 61.83 | Apache-2.0 |
| Quality candidate | `IEITYuan/Yuan-embedding-2.0-en` | 596M | 2.2 GB | 1,024 | 2,048 | 70.69 | Apache-2.0 |

### How to read the model specifications

| Property | Simple meaning | Effect on our decision |
| --- | --- | --- |
| Parameters | Number of learned values inside the model. For example, 596M means approximately 596 million learned values. | More parameters usually require more compute and memory, but do not automatically mean better retrieval. |
| Memory | Approximate memory needed for the model weights. Actual runtime usage is higher because inference also needs framework and working memory. | Helps determine whether the model fits on the deployment CPU or GPU and how expensive it may be to run. |
| Embedding dimensions | Number of values in the vector created for each chunk. A 384-dimensional embedding contains 384 numbers. | More dimensions increase vector-database storage and search cost. They may preserve more information, but do not guarantee better retrieval. |
| Maximum tokens | Hard limit on the text accepted in one embedding request. The title, heading path, chunk content, and any instruction all count toward it. | Places an upper bound on chunk size. We still use smaller, retrieval-focused chunks even when a model supports very long input. |
| Retrieval score | Aggregate retrieval result on the selected MTEB English-v2 tasks. Higher is better when the same benchmark and filters are used. | Provides a shortlist signal, not an expected success percentage for our Notion documents. Our own evaluation decides the winner. |

In short:

```text
Parameters  -> model compute complexity
Memory      -> capacity needed to run the model
Dimensions  -> vector storage and search cost
Max tokens  -> input and chunk-size ceiling
Score       -> public retrieval-quality signal
```

### BGE Small v1.5

BGE provides the deployment-cost baseline. It has far fewer parameters and a
smaller vector dimension than the other candidates. Its 384-dimensional
vectors require about 62.5% less raw vector storage than 1,024-dimensional
vectors when both use the same numeric representation.

Its disadvantages are the lowest leaderboard retrieval score in the shortlist
and a 512-token input limit. The chunker must reserve space within that limit
for the page title, heading path, and any retrieval instruction.

### Qwen3 Embedding 0.6B

Qwen3 is the balanced candidate because it combines a higher retrieval score
with mature documentation, configurable output dimensions, a long context
window, multilingual support, and documented deployment options.

The 32K context limit is a capacity ceiling, not a target chunk size. Notion
chunks should remain retrieval-focused and considerably smaller.

### Yuan Embedding 2.0 EN

Yuan is the quality candidate because it has the highest retrieval score in
the filtered shortlist. It is adapted from Qwen3 Embedding 0.6B for English
retrieval.

It requires additional validation because it is newer, has a less complete
model card, is English-specific, shows a higher memory requirement, and has
fewer documented deployment options. Its leaderboard result alone is not
enough to select it.

## Development-machine context

The development laptop has a Ryzen AI 7 350 CPU, 24 GB RAM, and an NVIDIA RTX
5050 Laptop GPU with about 8 GB VRAM. This is sufficient to evaluate the three
shortlisted models, although available memory, precision, batch size, and input
length will affect measured performance.

These local results support comparison only. Production sizing will depend on
ingestion volume, query traffic, latency, throughput, and infrastructure cost.

## Decision process from here

We will create representative Notion documents, including an oversized section,
and a labelled query set that identifies the expected relevant chunks. All
three models will then be tested with:

- the same normalized Notion documents and common chunks that fit every model;
- the same labelled queries and expected relevant chunks;
- each model's documented query instruction and normalization requirements;
- the same `k` values and comparable dense-vector search settings.

Each model's own tokenizer will count the complete `embedding_input`, including
instructions, page title, heading path, and chunk content. The oversized test
will record whether the input fits, how many fragments are required, and
whether any text would be truncated. Silent truncation is not allowed. The
selected model's token limit will then help determine the final chunk budget.

We will record these retrieval metrics:

| Metric | Meaning |
| --- | --- |
| Hit Rate@k | Percentage of queries with at least one relevant chunk in the top `k` results. |
| Precision@k | Percentage of the top `k` retrieved chunks that are relevant. |
| Recall@k | Percentage of all expected relevant chunks found in the top `k` results. |
| MRR | Measures how early the first relevant chunk appears; higher is better. |
| nDCG@k | Measures ranking quality by rewarding relevant chunks placed nearer the top. |

We will also record these operational metrics:

| Metric | Meaning |
| --- | --- |
| Query latency | Time required to embed a query and retrieve its top results. |
| Indexing time | Time required to embed and index the complete test corpus. |
| Peak memory | Highest memory usage observed while running the evaluation. |
| Vector storage | Space required to store the generated chunk vectors. |
| Input-limit compatibility | Whether every complete embedding input fits the model and how many splits oversized content requires. |

A qualitative review will confirm that retrieved chunks contain enough context
for citation and answer generation.

The final model will be recorded in an ADR only after this evaluation. A higher
MTEB score will not override substantially worse results on the target Notion
corpus or unacceptable deployment cost.

## References

- [MTEB leaderboard documentation](https://github.com/embeddings-benchmark/mteb/blob/main/docs/get_started/usage/leaderboard.md)
- [MTEB English v2 leaderboard](https://leaderboard.mteb.org/benchmark/MTEB%28eng%2C%20v2%29)
- [BGE Small model card](https://huggingface.co/BAAI/bge-small-en-v1.5)
- [Qwen3 Embedding 0.6B model card](https://huggingface.co/Qwen/Qwen3-Embedding-0.6B)
- [Yuan Embedding 2.0 EN model card](https://huggingface.co/IEITYuan/Yuan-embedding-2.0-en)
