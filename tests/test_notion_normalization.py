from typing import Any

from agentic_rag.ingestion.notion import (
    BlockSnapshot,
    NotionPageNormalizer,
    PageSnapshot,
)


def _rich_text(text: str, *, href: str | None = None) -> list[dict[str, Any]]:
    return [{"type": "text", "plain_text": text, "href": href}]


def _page(*blocks: BlockSnapshot) -> PageSnapshot:
    return PageSnapshot(
        value={
            "object": "page",
            "id": "payment-page",
            "url": "https://notion.so/payment-page",
            "last_edited_time": "2026-11-04T10:00:00.000Z",
            "parent": {"type": "page_id", "page_id": "root-page"},
            "properties": {
                "title": {
                    "type": "title",
                    "title": _rich_text("Payment Platform Architecture"),
                }
            },
        },
        blocks=blocks,
        child_page_ids=(),
    )


def test_normalize_creates_document_record_and_preserves_structure():
    paragraph = BlockSnapshot(
        value={
            "id": "paragraph-1",
            "type": "paragraph",
            "paragraph": {
                "rich_text": _rich_text(
                    "Provider documentation",
                    href="https://provider.example/docs",
                )
            },
        }
    )
    heading = BlockSnapshot(
        value={
            "id": "heading-1",
            "type": "heading_1",
            "heading_1": {"rich_text": _rich_text("Availability")},
        },
        children=(paragraph,),
    )

    document = NotionPageNormalizer("connection-1").normalize(_page(heading))

    assert document is not None
    assert document.record.document_id == "notion:connection-1:payment-page"
    assert document.record.page_title == "Payment Platform Architecture"
    assert document.record.parent_page_id == "root-page"
    assert document.record.omitted_block_types == ()
    assert document.blocks[0].properties == (("level", 1),)
    normalized_paragraph = document.blocks[0].children[0]
    assert normalized_paragraph.text == "Provider documentation"
    assert normalized_paragraph.references[0].target == "https://provider.example/docs"


def test_normalize_preserves_table_shape_and_header_flags():
    row = BlockSnapshot(
        value={
            "id": "row-1",
            "type": "table_row",
            "table_row": {
                "cells": [
                    _rich_text("Service"),
                    _rich_text("Owner"),
                ]
            },
        }
    )
    table = BlockSnapshot(
        value={
            "id": "table-1",
            "type": "table",
            "table": {
                "table_width": 2,
                "has_column_header": True,
                "has_row_header": False,
            },
        },
        children=(row,),
    )

    document = NotionPageNormalizer("connection-1").normalize(_page(table))

    assert document is not None
    assert dict(document.blocks[0].properties) == {
        "has_column_header": True,
        "has_row_header": False,
        "table_width": 2,
    }
    assert document.blocks[0].children[0].cells == ("Service", "Owner")


def test_normalize_preserves_child_page_and_page_link_meaning():
    child_page = BlockSnapshot(
        value={
            "id": "retry-page",
            "type": "child_page",
            "child_page": {"title": "Retry and Idempotency Design"},
        }
    )
    page_link = BlockSnapshot(
        value={
            "id": "link-1",
            "type": "link_to_page",
            "link_to_page": {"type": "page_id", "page_id": "ownership-page"},
        }
    )

    document = NotionPageNormalizer("connection-1").normalize(
        _page(child_page, page_link),
        page_titles_by_id={"ownership-page": "Service Ownership Matrix"},
    )

    assert document is not None
    assert document.blocks[0].references[0].target == "retry-page"
    assert document.blocks[1].text == "Service Ownership Matrix"
    assert document.blocks[1].references[0].target == "ownership-page"


def test_normalize_records_unsupported_blocks_and_skips_their_subtrees():
    unsupported = BlockSnapshot(
        value={"id": "image-1", "type": "image", "image": {}},
        children=(
            BlockSnapshot(
                value={
                    "id": "hidden-paragraph",
                    "type": "paragraph",
                    "paragraph": {"rich_text": _rich_text("Do not include")},
                }
            ),
        ),
    )
    paragraph = BlockSnapshot(
        value={
            "id": "paragraph-1",
            "type": "paragraph",
            "paragraph": {"rich_text": _rich_text("Include this")},
        }
    )

    document = NotionPageNormalizer("connection-1").normalize(
        _page(unsupported, paragraph)
    )

    assert document is not None
    assert document.record.omitted_block_types == ("image",)
    assert [block.block_id for block in document.blocks] == ["paragraph-1"]


def test_normalize_returns_none_when_page_has_no_indexable_content():
    divider = BlockSnapshot(value={"id": "divider-1", "type": "divider", "divider": {}})

    document = NotionPageNormalizer("connection-1").normalize(_page(divider))

    assert document is None


def test_content_and_revision_ids_are_deterministic():
    paragraph = BlockSnapshot(
        value={
            "id": "paragraph-1",
            "type": "paragraph",
            "paragraph": {"rich_text": _rich_text("Stable content")},
        }
    )
    normalizer = NotionPageNormalizer("connection-1")

    first = normalizer.normalize(_page(paragraph))
    second = normalizer.normalize(_page(paragraph))

    assert first is not None
    assert second is not None
    assert first.record.content_hash == second.record.content_hash
    assert first.record.revision_id == second.record.revision_id
