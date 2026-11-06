import hashlib
import json
import re
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

from agentic_rag.ingestion.notion.normalization import (
    DocumentRecord,
    NormalizedBlock,
    NormalizedDocument,
)


class TokenCounter(Protocol):
    def count(self, text: str) -> int: ...


class ChunkingError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class ChunkingConfig:
    max_tokens: int
    overlap_tokens: int = 0
    chunking_version: str = "notion-structure-v1"
    embedding_prefix: str = ""

    def __post_init__(self) -> None:
        if self.max_tokens <= 0:
            raise ValueError("Maximum tokens must be positive")
        if self.overlap_tokens < 0:
            raise ValueError("Overlap tokens must not be negative")
        if self.overlap_tokens >= self.max_tokens:
            raise ValueError("Overlap must be smaller than the maximum token count")
        if not self.chunking_version.strip():
            raise ValueError("Chunking version must not be empty")


@dataclass(frozen=True, slots=True)
class ChunkRecord:
    chunk_id: str
    document_id: str
    revision_id: str
    chunk_index: int
    content: str
    embedding_input: str
    content_kind: str
    heading_path: tuple[str, ...]
    block_ids: tuple[str, ...]
    token_count: int
    chunking_version: str
    fragment_index: int | None
    overlap_token_count: int


@dataclass(frozen=True, slots=True)
class _Unit:
    content: str
    content_kind: str
    heading_path: tuple[str, ...]
    block_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class _TableUnit:
    block: NormalizedBlock
    heading_path: tuple[str, ...]
    heading_block_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class _DraftChunk:
    content: str
    content_kind: str
    heading_path: tuple[str, ...]
    block_ids: tuple[str, ...]
    fragment_index: int | None = None
    overlap_token_count: int = 0


class NotionChunker:
    def __init__(self, token_counter: TokenCounter, config: ChunkingConfig) -> None:
        self._token_counter = token_counter
        self._config = config

    def chunk(self, document: NormalizedDocument) -> tuple[ChunkRecord, ...]:
        drafts: list[_DraftChunk] = []
        pending: _DraftChunk | None = None

        def flush_pending() -> None:
            nonlocal pending
            if pending is not None:
                drafts.append(pending)
                pending = None

        for unit in _semantic_units(document.blocks):
            if isinstance(unit, _TableUnit):
                flush_pending()
                drafts.extend(self._chunk_table(document.record, unit))
                continue

            if unit.content_kind in {"code", "page_reference"}:
                flush_pending()
                drafts.extend(self._chunk_unit(document.record, unit))
                continue

            if not self._fits(document.record, unit.heading_path, unit.content):
                flush_pending()
                drafts.extend(self._chunk_unit(document.record, unit))
                continue

            candidate = _merge_drafts(pending, unit) if pending else None
            if candidate and self._fits(
                document.record,
                candidate.heading_path,
                candidate.content,
            ):
                pending = candidate
                continue

            flush_pending()
            pending = _DraftChunk(
                content=unit.content,
                content_kind=unit.content_kind,
                heading_path=unit.heading_path,
                block_ids=unit.block_ids,
            )

        flush_pending()
        return tuple(
            self._to_record(document.record, draft, index)
            for index, draft in enumerate(drafts)
        )

    def _chunk_unit(
        self,
        document: DocumentRecord,
        unit: _Unit,
    ) -> list[_DraftChunk]:
        if self._fits(document, unit.heading_path, unit.content):
            return [
                _DraftChunk(
                    content=unit.content,
                    content_kind=unit.content_kind,
                    heading_path=unit.heading_path,
                    block_ids=unit.block_ids,
                )
            ]

        pieces = self._split_to_fit(
            document,
            unit.heading_path,
            unit.content,
            prefer_lines=unit.content_kind == "code",
        )
        drafts: list[_DraftChunk] = []
        previous = ""
        for fragment_index, primary_content in enumerate(pieces):
            overlap = (
                self._overlap_suffix(previous)
                if fragment_index > 0 and self._config.overlap_tokens
                else ""
            )
            content = self._fit_overlap(
                document,
                unit.heading_path,
                overlap,
                primary_content,
            )
            used_overlap = content[: len(content) - len(primary_content)]
            drafts.append(
                _DraftChunk(
                    content=content,
                    content_kind=unit.content_kind,
                    heading_path=unit.heading_path,
                    block_ids=unit.block_ids,
                    fragment_index=fragment_index,
                    overlap_token_count=self._token_counter.count(used_overlap),
                )
            )
            previous = primary_content
        return drafts

    def _chunk_table(
        self,
        document: DocumentRecord,
        unit: _TableUnit,
    ) -> list[_DraftChunk]:
        rows = [
            child for child in unit.block.children if child.block_type == "table_row"
        ]
        if not rows:
            return []

        properties = dict(unit.block.properties)
        has_header = properties.get("has_column_header") is True
        header = rows[0] if has_header else None
        data_rows = rows[1:] if header else rows
        header_text = _render_table_row(header) if header else ""
        base_ids = unit.heading_block_ids + (unit.block.block_id,)

        if header and not self._fits(document, unit.heading_path, header_text):
            raise ChunkingError(
                "A table header does not fit within the configured token limit"
            )

        drafts: list[_DraftChunk] = []
        current_rows: list[NormalizedBlock] = []

        def flush_rows() -> None:
            if not current_rows:
                return
            selected = ([header] if header else []) + current_rows
            content = "\n".join(_render_table_row(row) for row in selected if row)
            block_ids = base_ids + tuple(row.block_id for row in selected if row)
            drafts.append(
                _DraftChunk(
                    content=content,
                    content_kind="table",
                    heading_path=unit.heading_path,
                    block_ids=_unique(block_ids),
                )
            )
            current_rows.clear()

        for row in data_rows:
            candidate_rows = current_rows + [row]
            selected = ([header] if header else []) + candidate_rows
            candidate = "\n".join(
                _render_table_row(selected_row)
                for selected_row in selected
                if selected_row
            )
            if self._fits(document, unit.heading_path, candidate):
                current_rows.append(row)
                continue

            flush_rows()
            single_row = "\n".join(
                text for text in (header_text, _render_table_row(row)) if text
            )
            if self._fits(document, unit.heading_path, single_row):
                current_rows.append(row)
                continue

            row_pieces = self._split_table_row(
                document,
                unit.heading_path,
                header_text,
                _render_table_row(row),
            )
            for fragment_index, piece in enumerate(row_pieces):
                content = "\n".join(text for text in (header_text, piece) if text)
                row_ids = (
                    base_ids + ((header.block_id,) if header else ()) + (row.block_id,)
                )
                drafts.append(
                    _DraftChunk(
                        content=content,
                        content_kind="table",
                        heading_path=unit.heading_path,
                        block_ids=_unique(row_ids),
                        fragment_index=fragment_index,
                    )
                )

        flush_rows()
        if not drafts and header:
            drafts.append(
                _DraftChunk(
                    content=header_text,
                    content_kind="table",
                    heading_path=unit.heading_path,
                    block_ids=_unique(base_ids + (header.block_id,)),
                )
            )
        return drafts

    def _split_table_row(
        self,
        document: DocumentRecord,
        heading_path: tuple[str, ...],
        header_text: str,
        row_text: str,
    ) -> list[str]:
        def fits_with_header(piece: str) -> bool:
            content = "\n".join(text for text in (header_text, piece) if text)
            return self._fits(document, heading_path, content)

        return _split_text(row_text, fits_with_header, prefer_lines=False)

    def _split_to_fit(
        self,
        document: DocumentRecord,
        heading_path: tuple[str, ...],
        content: str,
        *,
        prefer_lines: bool,
    ) -> list[str]:
        primary_limit = self._config.max_tokens - self._config.overlap_tokens
        context_tokens = self._token_counter.count(
            _embedding_input(
                document.page_title,
                heading_path,
                "",
                self._config.embedding_prefix,
            )
        )
        limit = (
            primary_limit
            if self._config.overlap_tokens and context_tokens < primary_limit
            else self._config.max_tokens
        )
        return _split_text(
            content,
            lambda piece: (
                self._input_token_count(
                    document,
                    heading_path,
                    piece,
                )
                <= limit
            ),
            prefer_lines=prefer_lines,
        )

    def _overlap_suffix(self, text: str) -> str:
        if not text:
            return ""
        words = re.findall(r"\S+\s*", text)
        selected: list[str] = []
        for word in reversed(words):
            candidate = word + "".join(selected)
            if self._token_counter.count(candidate) > self._config.overlap_tokens:
                break
            selected.insert(0, word)
        return "".join(selected)

    def _fit_overlap(
        self,
        document: DocumentRecord,
        heading_path: tuple[str, ...],
        overlap: str,
        primary_content: str,
    ) -> str:
        candidate = overlap + primary_content
        if self._fits(document, heading_path, candidate):
            return candidate

        words = re.findall(r"\S+\s*", overlap)
        while words:
            words.pop(0)
            candidate = "".join(words) + primary_content
            if self._fits(document, heading_path, candidate):
                return candidate
        return primary_content

    def _fits(
        self,
        document: DocumentRecord,
        heading_path: tuple[str, ...],
        content: str,
    ) -> bool:
        return (
            self._input_token_count(document, heading_path, content)
            <= self._config.max_tokens
        )

    def _input_token_count(
        self,
        document: DocumentRecord,
        heading_path: tuple[str, ...],
        content: str,
    ) -> int:
        embedding_input = _embedding_input(
            document.page_title,
            heading_path,
            content,
            self._config.embedding_prefix,
        )
        return self._token_counter.count(embedding_input)

    def _to_record(
        self,
        document: DocumentRecord,
        draft: _DraftChunk,
        chunk_index: int,
    ) -> ChunkRecord:
        embedding_input = _embedding_input(
            document.page_title,
            draft.heading_path,
            draft.content,
            self._config.embedding_prefix,
        )
        token_count = self._token_counter.count(embedding_input)
        if token_count > self._config.max_tokens:
            raise ChunkingError("Chunk exceeds the configured token limit")

        chunk_id_input = json.dumps(
            {
                "document_id": document.document_id,
                "revision_id": document.revision_id,
                "chunking_version": self._config.chunking_version,
                "chunk_index": chunk_index,
                "content_hash": hashlib.sha256(
                    draft.content.encode("utf-8")
                ).hexdigest(),
            },
            separators=(",", ":"),
            sort_keys=True,
        )
        return ChunkRecord(
            chunk_id=str(uuid.uuid5(uuid.NAMESPACE_URL, chunk_id_input)),
            document_id=document.document_id,
            revision_id=document.revision_id,
            chunk_index=chunk_index,
            content=draft.content,
            embedding_input=embedding_input,
            content_kind=draft.content_kind,
            heading_path=draft.heading_path,
            block_ids=draft.block_ids,
            token_count=token_count,
            chunking_version=self._config.chunking_version,
            fragment_index=draft.fragment_index,
            overlap_token_count=draft.overlap_token_count,
        )


class ApproximateTokenCounter:
    """Development-only counter; production must use the model tokenizer."""

    def count(self, text: str) -> int:
        return len(re.findall(r"\w+|[^\w\s]", text, flags=re.UNICODE))


def _semantic_units(
    blocks: tuple[NormalizedBlock, ...],
    heading_stack: tuple[tuple[int, str, str], ...] = (),
) -> list[_Unit | _TableUnit]:
    units: list[_Unit | _TableUnit] = []
    current_headings = list(heading_stack)

    for block in blocks:
        if block.block_type.startswith("heading_"):
            level = int(block.block_type[-1])
            current_headings = [item for item in current_headings if item[0] < level]
            current_headings.append((level, block.text, block.block_id))
            if block.children:
                units.extend(_semantic_units(block.children, tuple(current_headings)))
            continue

        heading_path = tuple(item[1] for item in current_headings if item[1])
        heading_ids = tuple(item[2] for item in current_headings)
        if block.block_type == "table":
            units.append(_TableUnit(block, heading_path, heading_ids))
            continue

        rendered = _render_block(block)
        if rendered:
            units.append(
                _Unit(
                    content=rendered,
                    content_kind=_content_kind(block.block_type),
                    heading_path=heading_path,
                    block_ids=_unique(heading_ids + (block.block_id,)),
                )
            )

        if block.children:
            units.extend(_semantic_units(block.children, tuple(current_headings)))

    return units


def _render_block(block: NormalizedBlock) -> str:
    if block.block_type == "bulleted_list_item":
        return f"- {block.text}" if block.text else ""
    if block.block_type == "numbered_list_item":
        return f"1. {block.text}" if block.text else ""
    if block.block_type == "to_do":
        checked = dict(block.properties).get("checked") is True
        return f"[{'x' if checked else ' '}] {block.text}" if block.text else ""
    return block.text


def _render_table_row(row: NormalizedBlock | None) -> str:
    return " | ".join(row.cells) if row else ""


def _content_kind(block_type: str) -> str:
    if block_type in {"bulleted_list_item", "numbered_list_item", "to_do"}:
        return "list"
    if block_type == "code":
        return "code"
    if block_type in {"child_page", "link_to_page"}:
        return "page_reference"
    return "prose"


def _merge_drafts(pending: _DraftChunk, unit: _Unit) -> _DraftChunk | None:
    if pending.heading_path != unit.heading_path:
        return None
    kinds = {pending.content_kind, unit.content_kind}
    return _DraftChunk(
        content=f"{pending.content}\n\n{unit.content}",
        content_kind=next(iter(kinds)) if len(kinds) == 1 else "mixed",
        heading_path=pending.heading_path,
        block_ids=_unique(pending.block_ids + unit.block_ids),
    )


def _embedding_input(
    page_title: str,
    heading_path: tuple[str, ...],
    content: str,
    prefix: str,
) -> str:
    parts = []
    if prefix.strip():
        parts.append(prefix.strip())
    parts.append(f"Title: {page_title}")
    if heading_path:
        parts.append(f"Section: {' > '.join(heading_path)}")
    parts.append(content)
    return "\n".join(parts)


def _split_text(
    text: str,
    fits: Callable[[str], bool],
    *,
    prefer_lines: bool,
) -> list[str]:
    if fits(text):
        return [text]

    preferred = text.splitlines(keepends=True) if prefer_lines else _sentences(text)
    pieces = _pack_parts(preferred, fits)
    if pieces is not None:
        return pieces

    words = re.findall(r"\S+\s*|\s+", text)
    pieces = _pack_parts(words, fits)
    if pieces is not None:
        return pieces

    return _split_characters(text, fits)


def _sentences(text: str) -> list[str]:
    matches = re.findall(r".+?(?:[.!?](?=\s|$)\s*|$)", text, flags=re.DOTALL)
    return matches or [text]


def _pack_parts(
    parts: list[str],
    fits: Callable[[str], bool],
) -> list[str] | None:
    if not parts or any(not fits(part) for part in parts if part):
        return None

    packed: list[str] = []
    current = ""
    for part in parts:
        candidate = current + part
        if current and not fits(candidate):
            packed.append(current)
            current = part
        else:
            current = candidate
    if current:
        packed.append(current)
    return packed


def _split_characters(text: str, fits: Callable[[str], bool]) -> list[str]:
    pieces: list[str] = []
    start = 0
    while start < len(text):
        low = start + 1
        high = len(text)
        best = start
        while low <= high:
            middle = (low + high) // 2
            candidate = text[start:middle]
            if fits(candidate):
                best = middle
                low = middle + 1
            else:
                high = middle - 1
        if best == start:
            raise ChunkingError("Generated context leaves no room for source content")
        pieces.append(text[start:best])
        start = best
    return pieces


def _unique(values: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(values))
