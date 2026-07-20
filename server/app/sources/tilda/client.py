import re
import time
from typing import Any, Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings
from app.sources.tilda.config import TildaSource, get_tilda_sources


class TildaCatalogClient:
    """Fetches product lists from Tilda Store API."""

    def __init__(self, base_url: Optional[str] = None, timeout: Optional[float] = None):
        self.base_url = base_url or settings.tilda_api_base
        self.timeout = timeout or settings.http_timeout_sec

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8))
    async def fetch_products(self, source: TildaSource, size: int = 100) -> list[dict[str, Any]]:
        params = {
            "storepartuid": source.storepartuid,
            "recid": source.recid,
            "c": int(time.time() * 1000),
            "getparts": "true",
            "getoptions": "true",
            "size": size,
            "flag_root": "withroot",
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.get(self.base_url, params=params)
            response.raise_for_status()
            payload = response.json()
        return self._extract_products(payload)

    def _extract_products(self, payload: Any) -> list[dict[str, Any]]:
        if isinstance(payload, list):
            return [p for p in payload if isinstance(p, dict)]
        if not isinstance(payload, dict):
            return []
        for key in ("products", "items", "result", "data"):
            value = payload.get(key)
            if isinstance(value, list):
                return [p for p in value if isinstance(p, dict)]
            if isinstance(value, dict):
                nested = value.get("products") or value.get("items")
                if isinstance(nested, list):
                    return [p for p in nested if isinstance(p, dict)]
        # Some Tilda responses nest under parts
        parts = payload.get("parts")
        if isinstance(parts, list):
            products: list[dict[str, Any]] = []
            for part in parts:
                if isinstance(part, dict) and isinstance(part.get("products"), list):
                    products.extend(p for p in part["products"] if isinstance(p, dict))
            if products:
                return products
        return []


def gallery_urls(product: dict[str, Any]) -> list[str]:
    """Collect image URLs from gallery / editions / photo fields."""
    urls: list[str] = []
    gallery = product.get("gallery") or product.get("galleryjson") or []
    if isinstance(gallery, str):
        # sometimes JSON string
        import json

        try:
            gallery = json.loads(gallery)
        except Exception:
            gallery = []
    if isinstance(gallery, list):
        for item in gallery:
            if isinstance(item, str) and item.startswith("http"):
                urls.append(item)
            elif isinstance(item, dict):
                for key in ("img", "image", "url", "src"):
                    val = item.get(key)
                    if isinstance(val, str) and val.startswith("http"):
                        urls.append(val)
                        break
    for key in ("photo", "image", "img"):
        val = product.get(key)
        if isinstance(val, str) and val.startswith("http") and val not in urls:
            urls.insert(0, val)
    # Deduplicate preserving order
    seen: set[str] = set()
    result: list[str] = []
    for u in urls:
        if u not in seen:
            seen.add(u)
            result.append(u)
    return result


def product_uid(product: dict[str, Any]) -> str:
    for key in ("uid", "productuid", "id", "externalid"):
        val = product.get(key)
        if val is not None:
            return str(val)
    title = str(product.get("title") or product.get("name") or "unknown")
    return re.sub(r"\W+", "-", title.lower())


def product_price(product: dict[str, Any]) -> Optional[int]:
    for key in ("price", "price_min", "priceold"):
        val = product.get(key)
        if val is None or val == "":
            continue
        try:
            # Tilda often stores price in kopecks-like or as string
            num = float(str(val).replace(" ", "").replace(",", "."))
            if num > 100_000_000:  # likely kopecks
                return int(num // 100)
            if num > 10_000:
                return int(num)
            return int(num)
        except ValueError:
            continue
    return None


def product_url(product: dict[str, Any], source: TildaSource) -> str:
    slug = product.get("url") or product.get("alias") or product.get("slug") or ""
    if isinstance(slug, str) and slug.startswith("http"):
        return slug
    if isinstance(slug, str) and slug:
        return f"https://avgst.ru{slug if slug.startswith('/') else '/' + slug}"
    uid = product_uid(product)
    return f"https://avgst.ru{source.catalog_path}/tproduct/{uid}"


async def fetch_all_sources(client: Optional[TildaCatalogClient] = None) -> dict[str, list[dict]]:
    client = client or TildaCatalogClient()
    result: dict[str, list[dict]] = {}
    for source in get_tilda_sources():
        result[source.key] = await client.fetch_products(source)
    return result
