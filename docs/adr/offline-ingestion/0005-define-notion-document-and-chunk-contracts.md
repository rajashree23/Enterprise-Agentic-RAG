# ADR-005: Define minimal Notion document and chunk contracts

## Status

Proposed

## Context

The first offline-ingestion implementation needs enough information to insert,
retrieve, filter, cite, replace, and delete Notion chunks. The contract should
remain independent of the embedding model and vector database without adding
fields that the initial implementation does not use.

## Decision

Represent an ingested Notion page with one `DocumentRecord` and each searchable
unit with one `ChunkRecord`. The embedding stage adds a vector to the chunk when
writing it to the selected vector database.

### DocumentRecord

`Notion-supplied` means the value is read directly from a Notion API response.
`Application-generated` means our application creates the value.
`Application-derived` means our application calculates or normalizes the value
using information supplied by Notion.

| Property | Produced by | Meaning and use |
| --- | --- | --- |
| `document_id` | Application-generated | Stable internal ID in the form `notion:{connection_id}:{page_id}`. It is used to select every chunk belonging to one page. |
| `source` | Application-generated | Source discriminator assigned by the ingestion adapter. It is `notion` for this ingestion scope. |
| `connection_id` | Application-generated | Internal ID assigned to the configured Notion connection that retrieved the page. It scopes filtering and deletion. This is not a Notion workspace or integration ID. |
| `page_id` | Notion-supplied | Stable Notion page ID used for synchronization and source lookup. |
| `page_title` | Application-derived | Plain-text page title extracted and normalized from the title property supplied by Notion. |
| `page_url` | Notion-supplied | Canonical page URL returned by Notion and used to resolve citations. |
| `parent_page_id` | Application-derived | Parent page ID extracted from the Notion parent object when the parent is another supported page; otherwise it is absent. |
| `source_last_edited_at` | Notion-supplied | Last-edited timestamp reported by Notion and used as an initial change signal. |
| `content_hash` | Application-generated | Hash calculated from the normalized page title and all supported content, structure, and block provenance that can affect `content`, `embedding_input`, or `block_ids`. It confirms whether re-chunking is required. |
| `revision_id` | Application-generated | Deterministic ID calculated for the normalized page revision. |
| `omitted_block_types` | Application-derived | Unique unsupported block types skipped while reading the Notion page. |

`revision_id` is derived from document identity and normalized content using a
canonical encoding so field boundaries are unambiguous:

```text
revision_id = hash(canonical_encode(document_id, content_hash))
```

### ChunkRecord

The same `Notion-supplied`, `Application-generated`, and
`Application-derived` categories apply to chunk fields.

| Property | Produced by | Meaning and use |
| --- | --- | --- |
| `chunk_id` | Application-generated | Deterministic ID calculated by the chunker and used for idempotent vector upserts. |
| `document_id` | Application-generated | Parent document identity copied from `DocumentRecord`. It supports page-wide filtering, replacement, and deletion. |
| `revision_id` | Application-generated | Document revision copied from `DocumentRecord` to identify the revision from which the chunk was produced. |
| `chunk_index` | Application-generated | Zero-based position assigned by the chunker according to document reading order. |
| `content` | Application-derived | Faithful text assembled from supported Notion blocks. It is used as evidence and supplied to synthesis. |
| `embedding_input` | Application-generated | Text constructed for the embedding model from `content` plus context such as the page title and heading path. |
| `content_kind` | Application-derived | Category assigned from the contributing Notion block types: `prose`, `list`, `code`, `table`, `mixed`, or `page_reference`. |
| `heading_path` | Application-derived | Ordered heading text collected from the Notion page structure to provide section context. |
| `block_ids` | Application-derived | Notion-supplied block IDs collected for all source blocks that contributed content to the chunk. They provide block-level provenance. |
| `token_count` | Application-generated | Token count calculated from `embedding_input` using the selected embedding model's tokenizer. |
| `chunking_version` | Application-generated | Version of the chunking rules and configuration assigned by the application. |
| `fragment_index` | Application-generated | Optional zero-based fragment position assigned when one oversized semantic unit produces multiple chunks. |
| `overlap_token_count` | Application-generated | Number of source tokens repeated from the preceding fragment, calculated by the chunker. It is zero for ordinary chunks. |

The following document fields are duplicated in the vector payload because
they are needed directly after retrieval:

- `source`;
- `connection_id`;
- `page_id`;
- `page_title`; and
- `page_url`.

For indexed retrieval, the application must filter by the `connection_id`
values that the authenticated user is authorized to access. The authorization
filter is enforced by the deterministic retrieval layer, not by the LLM.

Resolving a citation through `page_url` or `block_ids` is subject to the same
authorization check; knowing a source URL or block ID does not grant access.

`chunk_id` is derived from stable chunk inputs using a canonical encoding:

```text
chunk_id = uuid5(
    canonical_encode(
        document_id,
        revision_id,
        chunking_version,
        chunk_index,
        hash(content)
    )
)
```

### Vector-store record

The vector-store adapter writes:

```json
{
  "id": "{chunk_id}",
  "vector": [0.013, -0.204, 0.087],
  "payload": {
    "content": "Source-derived chunk content",
    "document_id": "notion:connection-1:page-123",
    "revision_id": "revision-7",
    "source": "notion",
    "connection_id": "connection-1",
    "page_id": "page-123",
    "page_title": "Notion Ingestion Design",
    "page_url": "https://notion.so/...",
    "content_kind": "prose",
    "heading_path": ["Failure Handling"],
    "block_ids": ["block-21"]
  }
}
```

The domain contracts do not contain database-specific collection or index
configuration.

## Oversized content and repeated context

Structure is the preferred boundary, but a single paragraph, list, code block,
or table unit may exceed the model-safe token limit. The chunker must not
truncate supported content.

The configured limit applies to the complete `embedding_input`, including the
page title, heading path, repeated source text, and other generated context.
The chunker reserves space for that context before determining how much source
content fits in a fragment. Generated context may be shortened
deterministically when necessary, but evidence `content` is not discarded.

Oversized content is split using block-specific boundaries:

- prose is split at complete sentence boundaries when possible, then at a word
  or token boundary;
- lists are split between complete list items when possible; an oversized item
  falls back to sentence, word, or token boundaries;
- code is split at line boundaries when possible, then at a token boundary;
  and
- tables are split between complete rows when possible.

For every oversized prose, list, or code unit, the chunker:

1. retains the ID of each source block whose content appears in the fragment;
2. gives every fragment the same source block ID when one block is divided
   across multiple fragments;
3. records fragment order through `fragment_index`; and
4. applies only bounded overlap from the preceding fragment.

Example:

```text
Oversized block

Fragment 0: [primary content -----------------------]
Fragment 1:                    [overlap][primary content --------]
Fragment 2:                                      [overlap][primary]
```

Each fragment includes the applicable page title and heading path in
`embedding_input`. That generated context is not added to evidence `content`.
Only repeated source text contributes to `overlap_token_count`, and the overlap
must fit within the configured token limit.

Ordinary chunks separated at headings or block boundaries have no overlap.
Overlap is not applied uniformly across the document.

Large tables use a different repetition rule:

- when Notion supplies `has_column_header = true`, the column-header row is
  repeated in every table chunk; otherwise, the chunker does not infer a
  header;
- complete data rows remain intact when possible; and
- a data row appears as primary content in only one chunk.

If one data row exceeds the available token budget, its cell content is split
using sentence, word, or token boundaries without dropping source content. A
repeated table header also counts toward the complete `embedding_input` token
limit.

Repeated table headers are structural context and are not counted as generic
prose overlap. Generic overlap is not applied between table chunks.

## Lifecycle operations

### Insert

Normalize the complete page and prepare its `DocumentRecord`, deterministic
chunks, and embeddings before publishing the result. Upsert the
`DocumentRecord` by `document_id` and each vector by `chunk_id`. Repeating the
same ingestion does not create duplicate records.

### Update

Use `source_last_edited_at` as a signal to fetch and normalize the complete
page. Calculate `content_hash` from the normalized page title, supported block
text and IDs, block order and nesting, heading structure, table structure, and
supported link or page-reference meaning.

If the hash is unchanged, update the `DocumentRecord` metadata without
re-chunking. If the hash changed, prepare the complete new chunk set and all
embeddings before replacing the previous chunks for `document_id`. A parsing,
chunking, or embedding failure leaves the previous indexed version unchanged.
Block-level patching is outside the first iteration.

### Delete

Delete the `DocumentRecord` and every vector matching:

```text
document_id = {document_id}
```

Deletion occurs only after a confirmed event, such as the page being trashed or
its access being revoked. Removing a configured connection deletes every
`DocumentRecord` and vector matching its `connection_id`. A timeout, rate
limit, or other transient Notion failure is not treated as deletion.

When access is revoked, authorization filtering must prevent retrieval
immediately even if physical cleanup completes later.

### Re-chunk or re-embed

A new `chunking_version` replaces the chunk set without changing the source
revision. A new embedding model can re-embed the existing chunks when their
complete `embedding_input` values fit its token limit. If they do not fit, the
application increments `chunking_version`, re-chunks the document, and then
generates new embeddings. Re-embedding alone does not change `revision_id` or
`chunk_id`.

## Deferred extensions

- Exact citation positions within blocks.
- Atomic revision switching and block-level updates.
- Detailed ingestion and chunk diagnostics.
- Page-level authorization beyond connection-level access.
- Extra hashes and embedding-model metadata on each chunk.

## Consequences

- The minimal contracts support insertion, retrieval, filtering, citation,
  replacement, and deletion.
- Citations identify the Notion page and contributing blocks, but not exact
  positions within those blocks.
- Oversized content is split without silently dropping content.
- A page change replaces all its chunks. Atomic switching and block-level
  updates are deferred.

## References

- [Notion page object](https://developers.notion.com/reference/page)
- [Notion block object](https://developers.notion.com/reference/block)
- [Notion rich-text object](https://developers.notion.com/reference/rich-text)
- [Retrieve block children](https://developers.notion.com/reference/get-block-children)
