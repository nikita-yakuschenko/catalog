"""Download and inspect project assets."""

from __future__ import annotations

import hashlib
import mimetypes
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import httpx
from PIL import Image
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings
from app.domain.models import AssetType, QualityStatus


def classify_gallery_index(index: int) -> AssetType:
    if index == 0:
        return AssetType.exterior
    if index == 1:
        return AssetType.floor_plan
    # Extra page photos — treat as secondary exteriors / details
    return AssetType.exterior


def safe_filename(url: str, checksum: str) -> str:
    path = urlparse(url).path
    ext = Path(path).suffix.lower() or ".jpg"
    if ext not in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
        ext = ".jpg"
    return f"{checksum[:16]}{ext}"


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8))
async def download_bytes(url: str) -> tuple[bytes, str]:
    max_bytes = settings.max_asset_size_mb * 1024 * 1024
    async with httpx.AsyncClient(timeout=settings.http_timeout_sec, follow_redirects=True) as client:
        async with client.stream("GET", url) as response:
            response.raise_for_status()
            mime = response.headers.get("content-type", "").split(";")[0].strip()
            chunks: list[bytes] = []
            total = 0
            async for chunk in response.aiter_bytes():
                total += len(chunk)
                if total > max_bytes:
                    raise ValueError(f"Asset too large: {url}")
                chunks.append(chunk)
    data = b"".join(chunks)
    if not mime or mime == "application/octet-stream":
        mime = mimetypes.guess_type(url)[0] or "image/jpeg"
    return data, mime


def analyze_image(path: Path) -> dict:
    with Image.open(path) as img:
        width, height = img.size
        dpi_info = img.info.get("dpi")
        dpi = None
        if isinstance(dpi_info, tuple) and dpi_info:
            dpi = int(dpi_info[0])
        return {
            "width": width,
            "height": height,
            "aspect_ratio": round(width / height, 4) if height else 0.0,
            "dpi": dpi,
            "format": (img.format or "JPEG").lower(),
        }


async def ensure_asset(
    url: str,
    project_dir: Path,
    sort_order: int,
) -> dict:
    """Download asset if missing; return metadata dict for ProjectAsset."""
    project_dir.mkdir(parents=True, exist_ok=True)
    data, mime = await download_bytes(url)
    checksum = hashlib.sha256(data).hexdigest()
    filename = safe_filename(url, checksum)
    local_path = project_dir / filename
    if not local_path.exists():
        local_path.write_bytes(data)
    else:
        # skip rewrite if same checksum file exists
        existing = hashlib.sha256(local_path.read_bytes()).hexdigest()
        if existing != checksum:
            local_path.write_bytes(data)

    try:
        meta = analyze_image(local_path)
        quality = QualityStatus.ok
        if meta["width"] < 800 or meta["height"] < 600:
            quality = QualityStatus.warning
    except Exception:
        meta = {"width": 0, "height": 0, "aspect_ratio": 0.0, "dpi": None}
        quality = QualityStatus.error

    asset_type = classify_gallery_index(sort_order)
    return {
        "type": asset_type,
        "source_url": url,
        "local_path": str(local_path),
        "mime_type": mime,
        "width": meta["width"],
        "height": meta["height"],
        "aspect_ratio": meta["aspect_ratio"],
        "file_size": local_path.stat().st_size,
        "dpi": meta.get("dpi"),
        "sort_order": sort_order,
        "is_primary": sort_order == 0 and asset_type == AssetType.exterior,
        "quality_status": quality,
        "checksum": checksum,
    }
