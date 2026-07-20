"""Recompress Chromium PDF images (Flate/raw → JPEG) without touching source assets."""

from __future__ import annotations

import io
import logging
from pathlib import Path

import fitz
from PIL import Image

logger = logging.getLogger(__name__)

# Skip tiny embeds (QR / icons) — JPEG would hurt scannability.
_SKIP_MAX_EDGE = 420
_DEFAULT_QUALITY = 86
_HIGH_QUALITY = 90


def _jpeg_quality(width: int, height: int) -> int:
    # Floor plans / detail shots are often taller or more "diagram-like".
    ratio = max(width, height) / max(1, min(width, height))
    if ratio > 1.6 and min(width, height) >= 700:
        return _HIGH_QUALITY
    return _DEFAULT_QUALITY


def optimize_pdf_images(pdf_path: Path, *, quality: int | None = None) -> dict:
    """
    Replace large FlateDecode/raw page images with DCT JPEG streams.
    Returns stats dict; writes optimized PDF in place (atomic via temp file).
    """
    pdf_path = Path(pdf_path)
    before = pdf_path.stat().st_size
    doc = fitz.open(pdf_path)
    replaced = 0
    skipped = 0
    tmp = pdf_path.with_suffix(".opt.pdf")

    try:
        seen: set[int] = set()
        jobs: list[tuple[fitz.Page, int, int, int]] = []
        for page in doc:
            for img in page.get_images(full=True):
                xref = img[0]
                if xref in seen:
                    continue
                seen.add(xref)
                jobs.append((page, xref, int(img[2]), int(img[3])))

        for page, xref, w, h in jobs:
            if max(w, h) <= _SKIP_MAX_EDGE:
                skipped += 1
                continue

            try:
                info = doc.extract_image(xref)
            except Exception:
                skipped += 1
                continue

            filt = (info.get("filter") or "").lower()
            if "dct" in filt and info.get("size", 0) < 1_200_000:
                skipped += 1
                continue

            try:
                pix = fitz.Pixmap(doc, xref)
                if pix.alpha:
                    pix = fitz.Pixmap(pix, 0)
                if pix.n >= 4 or (pix.colorspace and "CMYK" in str(pix.colorspace)):
                    pix = fitz.Pixmap(fitz.csRGB, pix)

                q = quality if quality is not None else _jpeg_quality(pix.width, pix.height)
                jpeg = pix.tobytes("jpeg", jpg_quality=q)
                old_size = info.get("size") or (pix.width * pix.height * max(pix.n, 3))
                if len(jpeg) >= old_size * 0.95:
                    skipped += 1
                    continue

                page.replace_image(xref, stream=jpeg)
                replaced += 1
            except Exception:
                skipped += 1
                continue

        doc.save(tmp, garbage=4, deflate=True, clean=True, pretty=False)
        doc.close()
        tmp.replace(pdf_path)
    except Exception:
        doc.close()
        if tmp.exists():
            tmp.unlink(missing_ok=True)
        raise

    after = pdf_path.stat().st_size
    stats = {
        "before_bytes": before,
        "after_bytes": after,
        "replaced": replaced,
        "skipped": skipped,
        "ratio": round(after / before, 3) if before else 0,
    }
    logger.info(
        "PDF image optimize: %.1fMB → %.1fMB (replaced=%s skipped=%s)",
        before / 1e6,
        after / 1e6,
        replaced,
        skipped,
    )
    return stats


def optimize_image_bytes(
    data: bytes,
    *,
    max_edge: int = 1800,
    quality: int = 85,
) -> tuple[bytes, str]:
    """
    Resize + re-encode a photo for HTML/PDF embed.
    Returns (bytes, mime). Keeps visual quality; strips EXIF.
    """
    with Image.open(io.BytesIO(data)) as img:
        img.load()
        if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
            background = Image.new("RGB", img.size, (255, 255, 255))
            rgba = img.convert("RGBA")
            background.paste(rgba, mask=rgba.split()[-1])
            img = background
        elif img.mode != "RGB":
            img = img.convert("RGB")

        w, h = img.size
        edge = max(w, h)
        if edge > max_edge:
            scale = max_edge / edge
            img = img.resize((max(1, int(w * scale)), max(1, int(h * scale))), Image.Resampling.LANCZOS)

        out = io.BytesIO()
        img.save(
            out,
            format="JPEG",
            quality=quality,
            optimize=True,
            progressive=True,
            subsampling=1,
        )
        return out.getvalue(), "image/jpeg"
