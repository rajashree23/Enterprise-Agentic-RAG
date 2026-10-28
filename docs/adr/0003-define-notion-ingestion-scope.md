# ADR-003: Define Notion ingestion scope

## Status

Accepted

## Context

The first indexed-retrieval use cases are architecture and design discovery,
which depend primarily on durable technical documentation. A clear source and
content boundary is required before designing ingestion, chunking, indexing,
and retrieval.

## Decision

The initial offline-ingestion capability will support Notion only. Each Notion
page is a separate source document, and relationships between parent and child
pages are preserved.

### Supported

- Page identity, title, URL, hierarchy, and source timestamps.
- Basic text and structural blocks: paragraphs, headings, quotes, callouts,
  code, lists, to-do items, toggles, dividers, columns, and simple tables.
- Nested content within supported blocks.
- Child pages, links, and mentions to other Notion pages.
- Displayed rich text and the meaning of its links or page references.

Document content and meaningful structure are preserved. Exact visual
appearance is not part of the supported contract.

### Out of scope

- Sources other than Notion, including GitHub and Slack.
- Notion databases, data sources, database views, database rows, and child
  databases.
- Images, video, audio, PDFs, presentations, spreadsheets, and other attached
  files.
- Embeds, link previews, bookmarks, and externally rendered content.
- Advanced, dynamic, application-specific, or API-unsupported blocks.
- Comments, discussions, activity, revision history, and exact visual-layout
  reproduction.
- OCR, diagram interpretation, transcription, and extraction from attachments.

Pages containing unsupported blocks remain eligible for ingestion. Supported blocks are indexed, while unsupported blocks are skipped and recorded as omissions. A page with no supported content is not indexed.

## Deferred decisions

Separate decisions will define page acquisition, normalization, chunking,
synchronization, authorization, indexing, embeddings, and retrieval.

## Consequences

- Initial ingestion can be optimized for Notion architecture and design
  documentation.
- Simple tables are supported, while Notion databases and attached files are
  not.
- A page may remain useful even when some of its blocks are unsupported.
- GitHub and other sources require later scope decisions.

## References

- [Notion block reference](https://developers.notion.com/reference/block)
- [Retrieve block children](https://developers.notion.com/reference/get-block-children)
