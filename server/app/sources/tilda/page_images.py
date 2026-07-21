"""Fetch extra project images from avgst.ru product pages."""

from __future__ import annotations

import html as html_lib
import re
from typing import Optional
from urllib.parse import urlparse

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings

# Skip site chrome / UI icons
_SKIP_RE = re.compile(
    r"(logo|icon|heart|favicon|social|web\.png|image_1\.jpg|/image\.jpg)",
    re.I,
)
_CDN_IMG_RE = re.compile(
    r"https://static\.tildacdn\.com/[a-z0-9\-_/]+\.(?:jpg|jpeg|png|webp)",
    re.I,
)
_RESIZE_PATH_RE = re.compile(r"/\-/(?:resizeb?|resize)[^/]*/[^/]*/", re.I)
_PAGE_SCAN_RE = re.compile(r"_page-\d+\.(?:jpg|jpeg|png|webp)", re.I)
_LI_IMG_URL_RE = re.compile(
    r"li_img(?:\\)?(?:&quot;|\"|:)\s*(?:\\)?(?:&quot;|\"|:)\s*(https://static\.tildacdn\.com/[^\"\\&]+)",
    re.I,
)
_LI_IMG_SIMPLE_RE = re.compile(
    r"li_img[^h]*(https://static\.tildacdn\.com/[a-z0-9\-_/]+\.(?:jpg|jpeg|png|webp))",
    re.I,
)


def _clean_url(raw: str) -> str:
    url = html_lib.unescape(raw).split("&quot;")[0].split('"')[0].strip()
    return url


def normalize_tilda_image_url(url: str) -> str:
    """Canonical URL without Tilda resize prefixes or query string."""
    url = _clean_url(url)
    url = _RESIZE_PATH_RE.sub("/", url)
    return url.split("?")[0].strip()


def image_dedupe_key(url: str) -> str:
    """Same file may appear as full URL and /-/resizeb/20x/… — key by filename."""
    path = urlparse(normalize_tilda_image_url(url)).path
    return path.rsplit("/", 1)[-1].lower()


def _skip_url(url: str, *, api_gallery_count: int) -> bool:
    if _SKIP_RE.search(url):
        return True
    if _RESIZE_PATH_RE.search(url) or "/-/resize" in url:
        return True
    # PDF page raster duplicate of the plan already in Store API gallery
    if api_gallery_count >= 2 and _PAGE_SCAN_RE.search(url):
        return True
    return False


def extract_slider_image_urls(page_html: str) -> list[str]:
    """Tilda product slider order (li_img fields in page JSON)."""
    urls: list[str] = []
    for pat in (_LI_IMG_URL_RE, _LI_IMG_SIMPLE_RE):
        for match in pat.finditer(page_html):
            url = _clean_url(match.group(1))
            if url.startswith("http"):
                urls.append(url)
    seen: set[str] = set()
    unique: list[str] = []
    for url in urls:
        key = image_dedupe_key(url)
        if key not in seen:
            seen.add(key)
            unique.append(normalize_tilda_image_url(url))
    return unique


def extract_page_image_urls(page_html: str, *, api_gallery_count: int = 0) -> list[str]:
    urls: list[str] = []
    for match in _CDN_IMG_RE.findall(page_html):
        url = _clean_url(match)
        if not url.startswith("http"):
            continue
        if _skip_url(url, api_gallery_count=api_gallery_count):
            continue
        urls.append(normalize_tilda_image_url(url))

    seen: set[str] = set()
    unique: list[str] = []
    for url in urls:
        key = image_dedupe_key(url)
        if key not in seen:
            seen.add(key)
            unique.append(url)
    return unique


def merge_project_image_urls(api_urls: list[str], page_html: str) -> list[str]:
    """
    Store API gallery first, then page slider (li_img), then other page URLs.
    Dedupe by filename; cap at max_sync_assets_per_project.
    """
    api_gallery_count = len(api_urls)
    merged: list[str] = []
    seen_keys: set[str] = set()

    def add(raw: str, *, from_api: bool = False) -> None:
        url = normalize_tilda_image_url(raw)
        if not from_api and _skip_url(url, api_gallery_count=api_gallery_count):
            return
        if from_api and _SKIP_RE.search(url):
            return
        key = image_dedupe_key(url)
        if key in seen_keys:
            return
        seen_keys.add(key)
        merged.append(url)

    for u in api_urls:
        add(u, from_api=True)
    for u in extract_slider_image_urls(page_html):
        add(u)
    for u in extract_page_image_urls(page_html, api_gallery_count=api_gallery_count):
        add(u)

    return merged[: settings.max_sync_assets_per_project]


@retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=1, min=1, max=4))
async def fetch_page_html(project_url: str, client: Optional[httpx.AsyncClient] = None) -> str:
    if not project_url:
        return ""
    owns = client is None
    client = client or httpx.AsyncClient(timeout=settings.http_timeout_sec, follow_redirects=True)
    try:
        response = await client.get(project_url)
        response.raise_for_status()
        return response.text
    finally:
        if owns:
            await client.aclose()


async def fetch_page_images(project_url: str, client: Optional[httpx.AsyncClient] = None) -> list[str]:
    """Legacy: unordered page URLs (prefer merge_project_image_urls + fetch_page_html)."""
    html = await fetch_page_html(project_url, client=client)
    return extract_page_image_urls(html)


async def fetch_merged_image_urls(
    project_url: str,
    api_urls: list[str],
    client: Optional[httpx.AsyncClient] = None,
) -> list[str]:
    html = await fetch_page_html(project_url, client=client)
    if not html:
        return list(api_urls)[: settings.max_sync_assets_per_project]
    return merge_project_image_urls(api_urls, html)
