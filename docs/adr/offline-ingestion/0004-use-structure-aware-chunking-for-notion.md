# ADR-004: Use structure-aware chunking for Notion documents

## Status

Proposed

## Context

Notion pages are structured block trees rather than plain text or Markdown
files. Headings define sections, while paragraphs, lists, toggles, code blocks,
columns, and tables carry distinct structural meaning. Chunking should preserve
that meaning while producing units suitable for embedding, retrieval, and
source citation.

### Chunking strategies considered

| Strategy | How it works | Advantages | Limitations for Notion |
| --- | --- | --- | --- |
| Fixed-size | Splits content into equal character or token windows. | Simple, fast, and predictable. | Can split headings from their content and break lists, code, tables, and page references. |
| Fixed-size with overlap | Uses equal windows and repeats part of the previous window. | Reduces context loss at arbitrary boundaries. | Duplicates content and citations without understanding Notion structure. |
| Recursive text splitting | Tries separators such as sections, paragraphs, sentences, and words before applying a size limit. | Preserves more natural text boundaries than fixed windows. | Treats content primarily as text and needs additional rules for block types and nested structures. |
| Sentence or paragraph based | Creates chunks from sentences or paragraphs and groups adjacent units. | Produces readable chunks with natural prose boundaries. | Individual units may be too small or too large, and non-prose blocks require separate handling. |
| Semantic | Uses embeddings or a model to detect topic changes and choose boundaries. | Can identify conceptual transitions that are not explicitly marked. | Adds model cost, latency, nondeterminism, and evaluation complexity; may ignore authoritative document structure. |
| Parent-child or hierarchical | Indexes small child chunks while retaining larger parent sections for context. | Can combine precise retrieval with broader answer context. | Increases storage, retrieval, deduplication, and citation complexity for the initial implementation. |
| Structure-aware | Uses the Notion block tree, headings, nesting, and block types as primary boundaries, with a size limit as a fallback. | Preserves author-defined meaning, supports block-specific rules, and maintains precise provenance. | Author-defined units may be too small or too large, so the strategy still requires configurable size bounds, merging, fallback splitting, and explicit handling for each supported block type. |

### Why structure-aware chunking fits Notion

Notion already provides explicit document structure through its API. Using
that structure avoids reconstructing boundaries from flattened text and keeps
the chunking process deterministic.

Structure-aware chunking is a good fit because it can:

- keep headings with the content they describe;
- preserve nested lists and toggle context;
- keep code blocks intact when possible;
- apply row-aware rules to simple tables;
- keep child pages as separate documents;
- retain block-level provenance for citations and document updates; and
- use token limits only when a structural unit is too large.

The proposed direction is therefore structure-aware chunking with a bounded
size fallback. Exact block rules, size limits, overlap, and chunk metadata will
be decided in the remaining sections of this ADR.
