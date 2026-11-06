import asyncio
import os

from agentic_rag.ingestion.notion import (
    ApproximateTokenCounter,
    ChunkingConfig,
    NotionChunker,
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


def _preview(text: str, *, limit: int = 180) -> str:
    flattened = " ".join(text.split())
    return flattened if len(flattened) <= limit else f"{flattened[:limit]}..."


async def main() -> None:
    api_key = _required_environment("NOTION_API_KEY")
    root_page_id = _required_environment("NOTION_ROOT_PAGE_ID")
    api_version = os.environ.get("NOTION_API_VERSION", "2026-03-11")
    connection_id = os.environ.get("NOTION_CONNECTION_ID", "local-preview")
    max_tokens = int(os.environ.get("NOTION_PREVIEW_MAX_TOKENS", "128"))
    overlap_tokens = int(os.environ.get("NOTION_PREVIEW_OVERLAP_TOKENS", "16"))

    async with NotionClient(api_key, api_version=api_version) as client:
        pages = await NotionPageAcquirer(client).fetch_descendants(root_page_id)

    titles = {page.page_id: _raw_page_title(page) for page in pages}
    normalizer = NotionPageNormalizer(connection_id)
    chunker = NotionChunker(
        ApproximateTokenCounter(),
        ChunkingConfig(
            max_tokens=max_tokens,
            overlap_tokens=overlap_tokens,
        ),
    )

    print("Notion chunking preview")
    print(f"Approximate max tokens: {max_tokens}")
    print(f"Approximate overlap tokens: {overlap_tokens}")
    print("Production evaluation will use each embedding model's tokenizer.")

    for page in pages:
        document = normalizer.normalize(page, page_titles_by_id=titles)
        if document is None:
            continue
        chunks = chunker.chunk(document)
        print(f"\n{document.record.page_title}: {len(chunks)} chunks")
        for chunk in chunks:
            section = " > ".join(chunk.heading_path) or "<page root>"
            fragment = (
                str(chunk.fragment_index)
                if chunk.fragment_index is not None
                else "none"
            )
            print(
                f"  [{chunk.chunk_index}] {chunk.content_kind}; "
                f"tokens={chunk.token_count}; section={section}; "
                f"fragment={fragment}; overlap={chunk.overlap_token_count}"
            )
            print(f"      blocks: {', '.join(chunk.block_ids)}")
            print(f"      content: {_preview(chunk.content)}")


if __name__ == "__main__":
    asyncio.run(main())
