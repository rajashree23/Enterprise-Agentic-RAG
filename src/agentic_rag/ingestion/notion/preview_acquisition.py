import asyncio
import os
from collections import Counter
from collections.abc import Iterable, Iterator

from agentic_rag.ingestion.notion import (
    BlockSnapshot,
    NotionClient,
    NotionPageAcquirer,
    PageSnapshot,
)


def _required_environment(name: str) -> str:
    value = os.environ.get(name)
    if value is None or not value.strip():
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value.strip()


def _page_title(page: dict[str, object]) -> str:
    properties = page.get("properties")
    if not isinstance(properties, dict):
        return "<unknown>"

    for property_value in properties.values():
        if not isinstance(property_value, dict):
            continue
        title_items = property_value.get("title")
        if not isinstance(title_items, list):
            continue
        title = "".join(
            item.get("plain_text", "")
            for item in title_items
            if isinstance(item, dict) and isinstance(item.get("plain_text"), str)
        )
        return title or "<untitled>"

    return "<unknown>"


def _walk_blocks(blocks: Iterable[BlockSnapshot]) -> Iterator[BlockSnapshot]:
    for block in blocks:
        yield block
        yield from _walk_blocks(block.children)


def _print_page_tree(
    page_id: str,
    pages_by_id: dict[str, PageSnapshot],
    *,
    depth: int = 0,
) -> None:
    page = pages_by_id[page_id]
    block_count = sum(1 for _ in _walk_blocks(page.blocks))
    print(f"{'  ' * depth}- {_page_title(page.value)} ({block_count} blocks)")
    for child_page_id in page.child_page_ids:
        if child_page_id in pages_by_id:
            _print_page_tree(child_page_id, pages_by_id, depth=depth + 1)


def _print_block_summary(page: PageSnapshot) -> None:
    block_types = Counter(
        block.value.get("type", "<unknown>") for block in _walk_blocks(page.blocks)
    )
    summary = ", ".join(
        f"{block_type}={count}" for block_type, count in sorted(block_types.items())
    )
    print(f"- {_page_title(page.value)}: {summary or 'no blocks'}")


def _print_page_links(
    pages: Iterable[PageSnapshot],
    titles_by_id: dict[str, str],
) -> None:
    links_found = False
    for page in pages:
        source_title = _page_title(page.value)
        for block in _walk_blocks(page.blocks):
            if block.value.get("type") != "link_to_page":
                continue
            details = block.value.get("link_to_page")
            if not isinstance(details, dict):
                continue
            target_id = details.get("page_id") or details.get("database_id")
            if not isinstance(target_id, str):
                continue
            target_title = titles_by_id.get(target_id, target_id)
            print(f"- {source_title} -> {target_title}")
            links_found = True

    if not links_found:
        print("- none")


async def main() -> None:
    api_key = _required_environment("NOTION_API_KEY")
    root_page_id = _required_environment("NOTION_ROOT_PAGE_ID")
    api_version = os.environ.get("NOTION_API_VERSION", "2026-03-11")

    async with NotionClient(api_key, api_version=api_version) as client:
        pages = await NotionPageAcquirer(client).fetch_descendants(
            root_page_id,
            include_root=True,
        )

    pages_by_id = {page.page_id: page for page in pages}
    titles_by_id = {page.page_id: _page_title(page.value) for page in pages}

    print("Notion acquisition preview")
    print("\nPage hierarchy")
    _print_page_tree(root_page_id, pages_by_id)

    print("\nBlock types by page")
    for page in pages[1:]:
        _print_block_summary(page)

    print("\nLinks to pages")
    _print_page_links(pages, titles_by_id)


if __name__ == "__main__":
    asyncio.run(main())
