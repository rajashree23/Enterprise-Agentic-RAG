from agentic_rag.ingestion.notion import (
    ChunkingConfig,
    DocumentRecord,
    NormalizedBlock,
    NormalizedDocument,
    NotionChunker,
)


class WordTokenCounter:
    def count(self, text: str) -> int:
        return len(text.split())


def _document(*blocks: NormalizedBlock) -> NormalizedDocument:
    return NormalizedDocument(
        record=DocumentRecord(
            document_id="notion:connection-1:payment",
            source="notion",
            connection_id="connection-1",
            page_id="payment",
            page_title="Payment Architecture",
            page_url="https://notion.so/payment",
            parent_page_id="root",
            source_last_edited_at="2026-11-04T10:00:00.000Z",
            content_hash="content-hash",
            revision_id="revision-id",
            omitted_block_types=(),
        ),
        blocks=blocks,
    )


def _chunker(*, max_tokens: int = 30, overlap_tokens: int = 0) -> NotionChunker:
    return NotionChunker(
        WordTokenCounter(),
        ChunkingConfig(
            max_tokens=max_tokens,
            overlap_tokens=overlap_tokens,
        ),
    )


def test_chunks_follow_heading_boundaries_and_merge_adjacent_blocks():
    document = _document(
        NormalizedBlock("heading-security", "heading_1", text="Security"),
        NormalizedBlock("paragraph-1", "paragraph", text="Use workload identity."),
        NormalizedBlock("paragraph-2", "paragraph", text="Never log credentials."),
        NormalizedBlock("heading-availability", "heading_1", text="Availability"),
        NormalizedBlock("paragraph-3", "paragraph", text="Target is 99.95 percent."),
    )

    chunks = _chunker().chunk(document)

    assert len(chunks) == 2
    assert chunks[0].heading_path == ("Security",)
    assert chunks[0].content == ("Use workload identity.\n\nNever log credentials.")
    assert chunks[0].block_ids == (
        "heading-security",
        "paragraph-1",
        "paragraph-2",
    )
    assert chunks[0].overlap_token_count == 0
    assert chunks[1].heading_path == ("Availability",)


def test_oversized_prose_is_split_with_bounded_overlap_and_no_truncation():
    source_words = [f"word-{index}" for index in range(18)]
    source = " ".join(source_words)
    document = _document(NormalizedBlock("large-paragraph", "paragraph", text=source))

    chunks = _chunker(max_tokens=9, overlap_tokens=2).chunk(document)

    assert len(chunks) > 1
    assert [chunk.fragment_index for chunk in chunks] == list(range(len(chunks)))
    assert all(chunk.token_count <= 9 for chunk in chunks)
    assert all(chunk.block_ids == ("large-paragraph",) for chunk in chunks)
    assert chunks[0].overlap_token_count == 0
    assert all(0 < chunk.overlap_token_count <= 2 for chunk in chunks[1:])

    primary_words: list[str] = []
    for chunk in chunks:
        words = chunk.content.split()
        primary_words.extend(words[chunk.overlap_token_count :])
    assert primary_words == source_words


def test_table_chunks_repeat_declared_header_and_keep_rows_whole():
    table = NormalizedBlock(
        "table-1",
        "table",
        properties=(("has_column_header", True), ("table_width", 2)),
        children=(
            NormalizedBlock(
                "header-row",
                "table_row",
                cells=("Service", "Owner"),
            ),
            NormalizedBlock(
                "payment-row",
                "table_row",
                cells=("Payment", "Platform"),
            ),
            NormalizedBlock(
                "ledger-row",
                "table_row",
                cells=("Ledger", "Finance"),
            ),
        ),
    )
    document = _document(
        NormalizedBlock("heading-ownership", "heading_1", text="Ownership"),
        table,
    )

    chunks = _chunker(max_tokens=11).chunk(document)

    assert len(chunks) == 2
    assert all(chunk.content.startswith("Service | Owner\n") for chunk in chunks)
    assert sum("Payment | Platform" in chunk.content for chunk in chunks) == 1
    assert sum("Ledger | Finance" in chunk.content for chunk in chunks) == 1
    assert all("header-row" in chunk.block_ids for chunk in chunks)
    assert all(chunk.content_kind == "table" for chunk in chunks)


def test_page_references_are_separate_chunks():
    document = _document(
        NormalizedBlock("paragraph-1", "paragraph", text="Related designs follow."),
        NormalizedBlock(
            "link-1",
            "link_to_page",
            text="Service Ownership Matrix",
        ),
    )

    chunks = _chunker().chunk(document)

    assert len(chunks) == 2
    assert chunks[1].content_kind == "page_reference"
    assert chunks[1].content == "Service Ownership Matrix"


def test_chunk_ids_are_deterministic():
    document = _document(
        NormalizedBlock("paragraph-1", "paragraph", text="Stable content")
    )
    chunker = _chunker()

    first = chunker.chunk(document)
    second = chunker.chunk(document)

    assert first == second
    assert first[0].chunk_id == second[0].chunk_id


def test_complete_embedding_input_respects_token_limit():
    document = _document(
        NormalizedBlock("heading-1", "heading_1", text="Long Section Name"),
        NormalizedBlock(
            "paragraph-1",
            "paragraph",
            text="one two three four five six seven eight",
        ),
    )

    chunks = _chunker(max_tokens=10).chunk(document)

    assert len(chunks) > 1
    assert all(chunk.token_count <= 10 for chunk in chunks)
    assert all(
        "Title: Payment Architecture" in chunk.embedding_input for chunk in chunks
    )
    assert all(
        "Section: Long Section Name" in chunk.embedding_input for chunk in chunks
    )
