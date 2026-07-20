"""Fetch extra project images from avgst.ru product pages."""

from __future__ import annotations

import html as html_lib
import re
from typing import Optional

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings

# Skip site chrome / UI icons
_SKIP_RE = re.compile(
    r"(logo|icon|heart|favicon|social|web\.png|image_1\.jpg|/image\.jpg)",
    re.I,
)
_LI_IMG_RE = re.compile(
    r"https://static\.tildacdn\.com/[a-z0-9\-_/]+\.(?:jpg|jpeg|png|webp)",
    re.I,
)


def _clean_url(raw: str) -> str:
    url = html_lib.unescape(raw).split("&quot;")[0].split('"')[0].strip()
    return url


def extract_page_image_urls(page_html: str) -> list[str]:
    urls: list[str] = []
    for match in _LI_IMG_RE.findall(page_html):
        url = _clean_url(match)
        if not url.startswith("http"):
            continue
        if _SKIP_RE.search(url):
            continue
        # Prefer large photos under /tild* folders, skip tiny UI assets
        if url.endswith(".png") and "tild" in url and "logo" not in url.lower():
            # keep png photos, skip obvious icons already filtered
            pass
        urls.append(url)

    seen: set[str] = set()
    unique: list[str] = []
    for url in urls:
        if url not in seen:
            seen.add(url)
            unique.append(url)
    return unique


@retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=1, max=4))
async def fetch_page_images(project_url: str, client: Optional[httpx.AsyncClient] = None) -> list[str]:
    if not project_url:
        return []
    owns = client is None
    client = client or httpx.AsyncClient(timeout=settings.http_timeout_sec, follow_redirects=True)
    try:
        response = await client.get(project_url)
        response.raise_for_status()
        return extract_page_image_urls(response.text)
    finally:
        if owns:
            await client.aclose()
