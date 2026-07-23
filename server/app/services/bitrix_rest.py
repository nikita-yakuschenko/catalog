"""Minimal Bitrix24 REST client (incoming webhook URL)."""

from __future__ import annotations

import logging
from typing import Any, Optional
from urllib.parse import urljoin

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class BitrixRestError(RuntimeError):
    def __init__(self, message: str, *, payload: Optional[dict[str, Any]] = None):
        super().__init__(message)
        self.payload = payload or {}


class BitrixRestClient:
    def __init__(self, base_url: str | None = None, timeout: float | None = None):
        url = (base_url if base_url is not None else settings.bitrix_rest_webhook_url).strip()
        if not url:
            raise BitrixRestError("BITRIX_REST_WEBHOOK_URL не задан")
        self.base_url = url if url.endswith("/") else url + "/"
        self.timeout = timeout if timeout is not None else float(settings.http_timeout_sec)

    async def call(self, method: str, params: Optional[dict[str, Any]] = None) -> Any:
        url = urljoin(self.base_url, method.lstrip("/"))
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(url, json=params or {})
            try:
                data = response.json()
            except Exception as exc:
                raise BitrixRestError(
                    f"Bitrix {method}: не JSON ({response.status_code})",
                    payload={"text": response.text[:500]},
                ) from exc
        if response.status_code >= 400 or data.get("error"):
            raise BitrixRestError(
                f"Bitrix {method}: {data.get('error') or response.status_code} "
                f"{data.get('error_description') or ''}".strip(),
                payload=data if isinstance(data, dict) else {},
            )
        return data.get("result")

    async def get_item(self, entity_type_id: int, item_id: int) -> dict[str, Any]:
        result = await self.call(
            "crm.item.get",
            {"entityTypeId": entity_type_id, "id": item_id, "useOriginalUfNames": "Y"},
        )
        item = (result or {}).get("item") if isinstance(result, dict) else None
        if not isinstance(item, dict):
            raise BitrixRestError("crm.item.get: пустой item", payload={"result": result})
        return item

    async def get_contact(self, contact_id: int) -> dict[str, Any]:
        result = await self.call("crm.contact.get", {"id": contact_id})
        return result if isinstance(result, dict) else {}

    async def get_user(self, user_id: int) -> dict[str, Any]:
        result = await self.call("user.get", {"ID": user_id})
        if isinstance(result, list) and result:
            first = result[0]
            return first if isinstance(first, dict) else {}
        return result if isinstance(result, dict) else {}

    async def get_disk_file(self, file_id: int) -> dict[str, Any]:
        result = await self.call("disk.file.get", {"id": file_id})
        return result if isinstance(result, dict) else {}

    async def download_url(self, url: str) -> bytes:
        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.content

    async def download_disk_file(self, file_id: int) -> tuple[bytes, str]:
        meta = await self.get_disk_file(file_id)
        download = meta.get("DOWNLOAD_URL") or meta.get("downloadUrl") or ""
        name = str(meta.get("NAME") or meta.get("name") or f"file-{file_id}")
        if not download:
            raise BitrixRestError(f"disk.file.get #{file_id}: нет DOWNLOAD_URL", payload=meta)
        content = await self.download_url(str(download))
        return content, name

    async def upload_folder_file(
        self,
        folder_id: int,
        filename: str,
        content: bytes,
        *,
        generate_unique_name: bool = True,
    ) -> dict[str, Any]:
        import base64

        encoded = base64.b64encode(content).decode("ascii")
        result = await self.call(
            "disk.folder.uploadfile",
            {
                "id": folder_id,
                "data": {"NAME": filename},
                "fileContent": [filename, encoded],
                "generateUniqueName": generate_unique_name,
            },
        )
        return result if isinstance(result, dict) else {"result": result}

    async def update_item_fields(
        self, entity_type_id: int, item_id: int, fields: dict[str, Any]
    ) -> Any:
        return await self.call(
            "crm.item.update",
            {
                "entityTypeId": entity_type_id,
                "id": item_id,
                "fields": fields,
                "useOriginalUfNames": "Y",
            },
        )
