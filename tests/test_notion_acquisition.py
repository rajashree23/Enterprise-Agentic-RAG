from typing import Any

import pytest

from agentic_rag.ingestion.notion import NotionPageAcquirer


class FakeNotionReader:
    def __init__(
        self,
        *,
        pages: dict[str, dict[str, Any]],
        children: dict[str, list[dict[str, Any]]],
    ) -> None:
        self.pages = pages
        self.children = children
        self.children_requests: list[str] = []

    async def retrieve_page(self, page_id: str) -> dict[str, Any]:
        return self.pages[page_id]

    async def list_block_children(self, block_id: str) -> list[dict[str, Any]]:
        self.children_requests.append(block_id)
        return self.children.get(block_id, [])


@pytest.mark.asyncio
async def test_fetch_page_recurses_into_blocks_but_not_child_pages():
    reader = FakeNotionReader(
        pages={"payment": {"object": "page", "id": "payment"}},
        children={
            "payment": [
                {
                    "object": "block",
                    "id": "toggle-1",
                    "type": "toggle",
                    "has_children": True,
                },
                {
                    "object": "block",
                    "id": "retry",
                    "type": "child_page",
                    "has_children": True,
                },
            ],
            "toggle-1": [
                {
                    "object": "block",
                    "id": "paragraph-1",
                    "type": "paragraph",
                    "has_children": False,
                }
            ],
        },
    )

    page = await NotionPageAcquirer(reader).fetch_page("payment")

    assert page.page_id == "payment"
    assert page.child_page_ids == ("retry",)
    assert page.blocks[0].children[0].value["id"] == "paragraph-1"
    assert reader.children_requests == ["payment", "toggle-1"]


@pytest.mark.asyncio
async def test_fetch_descendants_keeps_each_page_separate():
    reader = FakeNotionReader(
        pages={
            "root": {"object": "page", "id": "root"},
            "payment": {"object": "page", "id": "payment"},
            "retry": {"object": "page", "id": "retry"},
        },
        children={
            "root": [
                {
                    "id": "payment",
                    "type": "child_page",
                    "has_children": True,
                }
            ],
            "payment": [
                {
                    "id": "retry",
                    "type": "child_page",
                    "has_children": True,
                },
                {
                    "id": "service-ownership-link",
                    "type": "link_to_page",
                    "has_children": False,
                    "link_to_page": {"type": "page_id", "page_id": "service"},
                },
            ],
            "retry": [],
        },
    )

    pages = await NotionPageAcquirer(reader).fetch_descendants("root")

    assert [page.page_id for page in pages] == ["payment", "retry"]
    assert pages[0].child_page_ids == ("retry",)
    assert "service" not in [page.page_id for page in pages]


@pytest.mark.asyncio
async def test_fetch_descendants_can_include_root_page():
    reader = FakeNotionReader(
        pages={"root": {"object": "page", "id": "root"}},
        children={"root": []},
    )

    pages = await NotionPageAcquirer(reader).fetch_descendants(
        "root",
        include_root=True,
    )

    assert [page.page_id for page in pages] == ["root"]
