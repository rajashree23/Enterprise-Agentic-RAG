from collections import deque
from dataclasses import dataclass
from typing import Any, Protocol


class NotionReader(Protocol):
    async def retrieve_page(self, page_id: str) -> dict[str, Any]: ...

    async def list_block_children(self, block_id: str) -> list[dict[str, Any]]: ...


@dataclass(frozen=True, slots=True)
class BlockSnapshot:
    """One Notion block plus any nested blocks owned by the same page."""

    value: dict[str, Any]
    children: tuple["BlockSnapshot", ...] = ()


@dataclass(frozen=True, slots=True)
class PageSnapshot:
    """Raw page data acquired before normalization or chunking."""

    value: dict[str, Any]
    blocks: tuple[BlockSnapshot, ...]
    child_page_ids: tuple[str, ...]

    @property
    def page_id(self) -> str:
        page_id = self.value.get("id")
        if not isinstance(page_id, str) or not page_id:
            raise ValueError("Notion page response omitted its ID")
        return page_id


class NotionPageAcquirer:
    """Fetch pages and their block trees without crossing page boundaries."""

    def __init__(self, reader: NotionReader) -> None:
        self._reader = reader

    async def fetch_page(self, page_id: str) -> PageSnapshot:
        page = await self._reader.retrieve_page(page_id)
        child_page_ids: list[str] = []
        blocks = await self._fetch_children(page_id, child_page_ids)
        return PageSnapshot(
            value=page,
            blocks=blocks,
            child_page_ids=tuple(dict.fromkeys(child_page_ids)),
        )

    async def fetch_descendants(
        self,
        root_page_id: str,
        *,
        include_root: bool = False,
    ) -> tuple[PageSnapshot, ...]:
        """Fetch each descendant page once in breadth-first reading order."""

        root = await self.fetch_page(root_page_id)
        pages: list[PageSnapshot] = [root] if include_root else []
        pending = deque(root.child_page_ids)
        seen = {root.page_id}

        while pending:
            page_id = pending.popleft()
            if page_id in seen:
                continue

            page = await self.fetch_page(page_id)
            seen.add(page_id)
            pages.append(page)
            pending.extend(page.child_page_ids)

        return tuple(pages)

    async def _fetch_children(
        self,
        parent_id: str,
        child_page_ids: list[str],
    ) -> tuple[BlockSnapshot, ...]:
        snapshots: list[BlockSnapshot] = []

        for block in await self._reader.list_block_children(parent_id):
            block_id = block.get("id")
            block_type = block.get("type")
            if not isinstance(block_id, str) or not block_id:
                raise ValueError("Notion block response omitted its ID")
            if not isinstance(block_type, str) or not block_type:
                raise ValueError("Notion block response omitted its type")

            if block_type == "child_page":
                child_page_ids.append(block_id)
                snapshots.append(BlockSnapshot(value=block))
                continue

            # A child database is out of scope and is also a separate object.
            # Neither separate-object type is traversed as content of this page.
            has_children = block.get("has_children") is True
            children = (
                await self._fetch_children(block_id, child_page_ids)
                if has_children and block_type != "child_database"
                else ()
            )
            snapshots.append(BlockSnapshot(value=block, children=children))

        return tuple(snapshots)
