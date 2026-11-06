from collections.abc import Mapping
from typing import Any, Self

import httpx


class NotionApiError(RuntimeError):
    def __init__(self, status_code: int, code: str) -> None:
        super().__init__(f"Notion API returned HTTP {status_code} ({code})")
        self.status_code = status_code
        self.code = code


class NotionClient:
    """Minimal read-only client for the Notion page and block APIs."""

    def __init__(
        self,
        api_key: str,
        *,
        api_version: str = "2026-03-11",
        base_url: str = "https://api.notion.com/v1",
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        if not api_key.strip():
            raise ValueError("Notion API key must not be empty")

        self._headers = {
            "Authorization": f"Bearer {api_key}",
            "Notion-Version": api_version,
            "Accept": "application/json",
        }
        self._client = http_client or httpx.AsyncClient(
            base_url=base_url,
            timeout=20.0,
        )
        self._owns_client = http_client is None

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *args: object) -> None:
        if self._owns_client:
            await self._client.aclose()

    async def retrieve_page(self, page_id: str) -> dict[str, Any]:
        payload = await self._get(f"/pages/{page_id}")
        if payload.get("object") != "page":
            raise ValueError("Notion returned an invalid page response")
        return payload

    async def list_block_children(self, block_id: str) -> list[dict[str, Any]]:
        blocks: list[dict[str, Any]] = []
        start_cursor: str | None = None

        while True:
            params: dict[str, str | int] = {"page_size": 100}
            if start_cursor is not None:
                params["start_cursor"] = start_cursor

            payload = await self._get(
                f"/blocks/{block_id}/children",
                params=params,
            )
            results = payload.get("results")
            has_more = payload.get("has_more")

            if not isinstance(results, list) or not isinstance(has_more, bool):
                raise TypeError("Notion returned an invalid block-list response")
            if not all(isinstance(block, dict) for block in results):
                raise ValueError("Notion returned a non-object block")

            blocks.extend(results)
            if not has_more:
                return blocks

            start_cursor = payload.get("next_cursor")
            if not isinstance(start_cursor, str) or not start_cursor:
                raise ValueError("Notion omitted the next pagination cursor")

    async def _get(
        self,
        path: str,
        *,
        params: Mapping[str, str | int] | None = None,
    ) -> dict[str, Any]:
        response = await self._client.get(
            path,
            params=params,
            headers=self._headers,
        )

        try:
            payload = response.json()
        except ValueError as exc:
            raise ValueError("Notion returned a non-JSON response") from exc

        if response.is_error:
            code = payload.get("code") if isinstance(payload, dict) else None
            raise NotionApiError(
                response.status_code,
                code if isinstance(code, str) else "unknown_error",
            )
        if not isinstance(payload, dict):
            raise TypeError("Notion returned a non-object response")

        return payload
