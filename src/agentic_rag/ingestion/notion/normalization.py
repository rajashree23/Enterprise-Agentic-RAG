import hashlib
import json
from dataclasses import dataclass
from typing import Any

from agentic_rag.ingestion.notion.acquisition import (
    BlockSnapshot,
    PageSnapshot,
)

SUPPORTED_BLOCK_TYPES = frozenset(
    {
        "paragraph",
        "heading_1",
        "heading_2",
        "heading_3",
        "bulleted_list_item",
        "numbered_list_item",
        "to_do",
        "toggle",
        "quote",
        "callout",
        "code",
        "divider",
        "column_list",
        "column",
        "table",
        "table_row",
        "child_page",
        "link_to_page",
    }
)


@dataclass(frozen=True, slots=True)
class ContentReference:
    kind: str
    target: str
    displayed_text: str


@dataclass(frozen=True, slots=True)
class NormalizedBlock:
    block_id: str
    block_type: str
    text: str = ""
    cells: tuple[str, ...] = ()
    references: tuple[ContentReference, ...] = ()
    properties: tuple[tuple[str, str | bool | int], ...] = ()
    children: tuple["NormalizedBlock", ...] = ()


@dataclass(frozen=True, slots=True)
class DocumentRecord:
    document_id: str
    source: str
    connection_id: str
    page_id: str
    page_title: str
    page_url: str
    parent_page_id: str | None
    source_last_edited_at: str
    content_hash: str
    revision_id: str
    omitted_block_types: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class NormalizedDocument:
    record: DocumentRecord
    blocks: tuple[NormalizedBlock, ...]


class NotionPageNormalizer:
    def __init__(self, connection_id: str) -> None:
        if not connection_id.strip():
            raise ValueError("Connection ID must not be empty")
        self._connection_id = connection_id.strip()

    def normalize(
        self,
        page: PageSnapshot,
        *,
        page_titles_by_id: dict[str, str] | None = None,
    ) -> NormalizedDocument | None:
        omitted_block_types: set[str] = set()
        titles = page_titles_by_id or {}
        blocks = tuple(
            normalized
            for block in page.blocks
            if (
                normalized := self._normalize_block(
                    block,
                    titles,
                    omitted_block_types,
                )
            )
            is not None
        )

        if not any(_has_indexable_content(block) for block in blocks):
            return None

        page_title = _page_title(page.value)
        document_id = f"notion:{self._connection_id}:{page.page_id}"
        canonical_content = {
            "page_title": page_title,
            "blocks": [_canonical_block(block) for block in blocks],
        }
        content_hash = _sha256(canonical_content)
        revision_id = _sha256(
            {
                "document_id": document_id,
                "content_hash": content_hash,
            }
        )

        record = DocumentRecord(
            document_id=document_id,
            source="notion",
            connection_id=self._connection_id,
            page_id=page.page_id,
            page_title=page_title,
            page_url=_required_string(page.value, "url", "page URL"),
            parent_page_id=_parent_page_id(page.value),
            source_last_edited_at=_required_string(
                page.value,
                "last_edited_time",
                "last-edited timestamp",
            ),
            content_hash=content_hash,
            revision_id=revision_id,
            omitted_block_types=tuple(sorted(omitted_block_types)),
        )
        return NormalizedDocument(record=record, blocks=blocks)

    def _normalize_block(
        self,
        snapshot: BlockSnapshot,
        page_titles_by_id: dict[str, str],
        omitted_block_types: set[str],
    ) -> NormalizedBlock | None:
        block_id = _required_string(snapshot.value, "id", "block ID")
        block_type = _required_string(snapshot.value, "type", "block type")
        if block_type not in SUPPORTED_BLOCK_TYPES:
            omitted_block_types.add(block_type)
            return None

        details = snapshot.value.get(block_type)
        if not isinstance(details, dict):
            details = {}

        if block_type == "link_to_page":
            return self._normalize_page_link(
                block_id,
                details,
                page_titles_by_id,
                omitted_block_types,
            )

        if block_type == "child_page":
            title = details.get("title")
            displayed_text = title if isinstance(title, str) else ""
            return NormalizedBlock(
                block_id=block_id,
                block_type=block_type,
                text=displayed_text,
                references=(
                    ContentReference(
                        kind="page",
                        target=block_id,
                        displayed_text=displayed_text,
                    ),
                ),
            )

        text, references = _normalize_rich_text(details.get("rich_text"))
        properties: list[tuple[str, str | bool | int]] = []
        cells: tuple[str, ...] = ()

        if block_type.startswith("heading_"):
            properties.append(("level", int(block_type[-1])))
        elif block_type == "to_do":
            properties.append(("checked", details.get("checked") is True))
        elif block_type == "code":
            language = details.get("language")
            if isinstance(language, str):
                properties.append(("language", language))
        elif block_type == "table":
            properties.extend(
                (
                    ("has_column_header", details.get("has_column_header") is True),
                    ("has_row_header", details.get("has_row_header") is True),
                )
            )
            table_width = details.get("table_width")
            if isinstance(table_width, int):
                properties.append(("table_width", table_width))
        elif block_type == "table_row":
            cells, cell_references = _normalize_cells(details.get("cells"))
            references += cell_references

        children = tuple(
            normalized
            for child in snapshot.children
            if (
                normalized := self._normalize_block(
                    child,
                    page_titles_by_id,
                    omitted_block_types,
                )
            )
            is not None
        )

        return NormalizedBlock(
            block_id=block_id,
            block_type=block_type,
            text=text,
            cells=cells,
            references=references,
            properties=tuple(properties),
            children=children,
        )

    def _normalize_page_link(
        self,
        block_id: str,
        details: dict[str, Any],
        page_titles_by_id: dict[str, str],
        omitted_block_types: set[str],
    ) -> NormalizedBlock | None:
        if details.get("type") != "page_id":
            omitted_block_types.add("link_to_page")
            return None

        page_id = details.get("page_id")
        if not isinstance(page_id, str) or not page_id:
            raise ValueError("Notion page link omitted its target page ID")
        displayed_text = page_titles_by_id.get(page_id, page_id)
        return NormalizedBlock(
            block_id=block_id,
            block_type="link_to_page",
            text=displayed_text,
            references=(
                ContentReference(
                    kind="page",
                    target=page_id,
                    displayed_text=displayed_text,
                ),
            ),
        )


def _page_title(page: dict[str, Any]) -> str:
    properties = page.get("properties")
    if not isinstance(properties, dict):
        raise TypeError("Notion page response returned invalid properties")

    for property_value in properties.values():
        if not isinstance(property_value, dict):
            continue
        title_items = property_value.get("title")
        if isinstance(title_items, list):
            title, _ = _normalize_rich_text(title_items)
            if title:
                return title

    raise ValueError("Notion page response omitted its title")


def _normalize_rich_text(value: object) -> tuple[str, tuple[ContentReference, ...]]:
    if not isinstance(value, list):
        return "", ()

    text_parts: list[str] = []
    references: list[ContentReference] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        plain_text = item.get("plain_text")
        displayed_text = plain_text if isinstance(plain_text, str) else ""
        text_parts.append(displayed_text)

        mention = item.get("mention")
        if isinstance(mention, dict) and mention.get("type") == "page":
            page = mention.get("page")
            page_id = page.get("id") if isinstance(page, dict) else None
            if isinstance(page_id, str) and page_id:
                references.append(ContentReference("page", page_id, displayed_text))
                continue

        href = item.get("href")
        if isinstance(href, str) and href:
            references.append(ContentReference("url", href, displayed_text))

    return "".join(text_parts), tuple(references)


def _normalize_cells(
    value: object,
) -> tuple[tuple[str, ...], tuple[ContentReference, ...]]:
    if not isinstance(value, list):
        return (), ()

    cells: list[str] = []
    references: list[ContentReference] = []
    for cell in value:
        text, cell_references = _normalize_rich_text(cell)
        cells.append(text)
        references.extend(cell_references)
    return tuple(cells), tuple(references)


def _parent_page_id(page: dict[str, Any]) -> str | None:
    parent = page.get("parent")
    if not isinstance(parent, dict) or parent.get("type") != "page_id":
        return None
    page_id = parent.get("page_id")
    return page_id if isinstance(page_id, str) and page_id else None


def _required_string(value: dict[str, Any], key: str, label: str) -> str:
    result = value.get(key)
    if not isinstance(result, str) or not result:
        raise ValueError(f"Notion response omitted its {label}")
    return result


def _has_indexable_content(block: NormalizedBlock) -> bool:
    return bool(
        block.text.strip()
        or any(cell.strip() for cell in block.cells)
        or block.references
        or any(_has_indexable_content(child) for child in block.children)
    )


def _canonical_block(block: NormalizedBlock) -> dict[str, object]:
    return {
        "block_id": block.block_id,
        "block_type": block.block_type,
        "text": block.text,
        "cells": list(block.cells),
        "references": [
            {
                "kind": reference.kind,
                "target": reference.target,
                "displayed_text": reference.displayed_text,
            }
            for reference in block.references
        ],
        "properties": dict(block.properties),
        "children": [_canonical_block(child) for child in block.children],
    }


def _sha256(value: object) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()
