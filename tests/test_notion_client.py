import httpx
import pytest

from agentic_rag.ingestion.notion import NotionApiError, NotionClient


@pytest.mark.asyncio
async def test_retrieve_page_sends_authentication_and_version_headers():
    async def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == "Bearer test-token"
        assert request.headers["Notion-Version"] == "2026-03-11"
        return httpx.Response(200, json={"object": "page", "id": "page-id"})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="https://api.notion.test/v1",
    ) as http_client:
        client = NotionClient("test-token", http_client=http_client)
        page = await client.retrieve_page("page-id")

    assert page["id"] == "page-id"


@pytest.mark.asyncio
async def test_list_block_children_follows_pagination():
    requests: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if len(requests) == 1:
            return httpx.Response(
                200,
                json={
                    "object": "list",
                    "results": [{"object": "block", "id": "one"}],
                    "has_more": True,
                    "next_cursor": "next-page",
                },
            )
        return httpx.Response(
            200,
            json={
                "object": "list",
                "results": [{"object": "block", "id": "two"}],
                "has_more": False,
                "next_cursor": None,
            },
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="https://api.notion.test/v1",
    ) as http_client:
        client = NotionClient("test-token", http_client=http_client)
        blocks = await client.list_block_children("page-id")

    assert [block["id"] for block in blocks] == ["one", "two"]
    assert requests[1].url.params["start_cursor"] == "next-page"


@pytest.mark.asyncio
async def test_api_errors_do_not_expose_response_details():
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            403,
            json={
                "object": "error",
                "code": "restricted_resource",
                "message": "sensitive upstream detail",
            },
        )

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="https://api.notion.test/v1",
    ) as http_client:
        client = NotionClient("test-token", http_client=http_client)
        with pytest.raises(NotionApiError) as error:
            await client.retrieve_page("page-id")

    assert error.value.status_code == 403
    assert error.value.code == "restricted_resource"
    assert "sensitive upstream detail" not in str(error.value)
