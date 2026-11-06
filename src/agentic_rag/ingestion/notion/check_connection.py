import asyncio
import os

from agentic_rag.ingestion.notion import NotionClient


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
        text = "".join(
            item.get("plain_text", "")
            for item in title_items
            if isinstance(item, dict) and isinstance(item.get("plain_text"), str)
        )
        return text or "<untitled>"

    return "<unknown>"


async def main() -> None:
    api_key = _required_environment("NOTION_API_KEY")
    page_id = _required_environment("NOTION_ROOT_PAGE_ID")
    api_version = os.environ.get("NOTION_API_VERSION", "2026-03-11")

    async with NotionClient(api_key, api_version=api_version) as client:
        page = await client.retrieve_page(page_id)
        blocks = await client.list_block_children(page_id)

    child_pages = [block for block in blocks if block.get("type") == "child_page"]

    print("Notion connection verified")
    print(f"Root page: {_page_title(page)}")
    print(f"Direct blocks: {len(blocks)}")
    print(f"Direct child pages: {len(child_pages)}")
    for child in child_pages:
        details = child.get("child_page")
        title = details.get("title") if isinstance(details, dict) else None
        print(f"- {title if isinstance(title, str) else '<untitled>'}")


if __name__ == "__main__":
    asyncio.run(main())
