import asyncio
import os
from collections.abc import Iterable

from agentic_rag.ingestion.notion import (
    NormalizedBlock,
    NotionClient,
    NotionPageAcquirer,
    NotionPageNormalizer,
    PageSnapshot,
)


def _required_environment(name: str) -> str:
    value = os.environ.get(name)
    if value is None or not value.strip():
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value.strip()


def _raw_page_title(page: PageSnapshot) -> str:
    properties = page.value.get("properties")
    if not isinstance(properties, dict):
        return "<unknown>"
    for value in properties.values():
        if not isinstance(value, dict) or not isinstance(value.get("title"), list):
            continue
        return "".join(
            item.get("plain_text", "")
            for item in value["title"]
            if isinstance(item, dict) and isinstance(item.get("plain_text"), str)
        )
    return "<unknown>"


def _preview_text(text: str, *, limit: int = 120) -> str:
    normalized = " ".join(text.split())
    return normalized if len(normalized) <= limit else f"{normalized[:limit]}..."


def _print_blocks(blocks: Iterable[NormalizedBlock], *, depth: int = 1) -> None:
    for block in blocks:
        content = " | ".join(block.cells) if block.cells else block.text
        suffix = f': "{_preview_text(content)}"' if content else ""
        print(f"{'  ' * depth}- {block.block_type} [{block.block_id}]{suffix}")
        for reference in block.references:
            print(
                f"{'  ' * (depth + 1)}reference: {reference.kind} -> {reference.target}"
            )
        _print_blocks(block.children, depth=depth + 1)


async def main() -> None:
    api_key = _required_environment("NOTION_API_KEY")
    root_page_id = _required_environment("NOTION_ROOT_PAGE_ID")
    api_version = os.environ.get("NOTION_API_VERSION", "2026-03-11")
    connection_id = os.environ.get("NOTION_CONNECTION_ID", "local-preview")

    async with NotionClient(api_key, api_version=api_version) as client:
        pages = await NotionPageAcquirer(client).fetch_descendants(root_page_id)

    titles = {page.page_id: _raw_page_title(page) for page in pages}
    normalizer = NotionPageNormalizer(connection_id)

    print("Notion normalization preview")
    print(f"Connection ID: {connection_id}")
    for page in pages:
        document = normalizer.normalize(page, page_titles_by_id=titles)
        if document is None:
            print(f"\n{_raw_page_title(page)}: skipped (no indexable content)")
            continue

        record = document.record
        print(f"\n{record.page_title}")
        print(f"  document_id: {record.document_id}")
        print(f"  parent_page_id: {record.parent_page_id}")
        print(f"  content_hash: {record.content_hash}")
        print(f"  revision_id: {record.revision_id}")
        print(
            f"  omitted_block_types: {', '.join(record.omitted_block_types) or 'none'}"
        )
        print("  normalized blocks:")
        _print_blocks(document.blocks, depth=2)


if __name__ == "__main__":
    asyncio.run(main())
