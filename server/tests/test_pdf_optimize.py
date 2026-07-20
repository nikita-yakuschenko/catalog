"""Tests for PDF/image optimization used in catalog builds."""

from pathlib import Path

import fitz
from PIL import Image

from app.services.pdf_optimize import optimize_image_bytes, optimize_pdf_images


def test_optimize_image_bytes_shrinks_large_rgb(tmp_path: Path):
    img = Image.new("RGB", (2400, 1400), (40, 120, 80))
    raw = tmp_path / "big.png"
    img.save(raw, format="PNG")
    data, mime = optimize_image_bytes(raw.read_bytes(), max_edge=1200, quality=85)
    assert mime == "image/jpeg"
    assert len(data) < raw.stat().st_size
    out = Image.open(__import__("io").BytesIO(data))
    assert max(out.size) <= 1200


def test_optimize_pdf_images_recompresses_flate(tmp_path: Path):
    # Build a tiny PDF with a large Flate-like pixmap image (Chromium-style).
    pdf_path = tmp_path / "sample.pdf"
    doc = fitz.open()
    page = doc.new_page(width=600, height=400)
    # RGB without alpha
    pix = fitz.Pixmap(fitz.csRGB, fitz.IRect(0, 0, 800, 500), 0)
    pix.set_rect(pix.irect, (30, 90, 50))
    page.insert_image(page.rect, pixmap=pix)
    doc.save(pdf_path)
    doc.close()

    before = pdf_path.stat().st_size
    stats = optimize_pdf_images(pdf_path, quality=85)
    after = pdf_path.stat().st_size
    assert stats["replaced"] >= 1
    assert after < before

    doc = fitz.open(pdf_path)
    assert doc.page_count == 1
    doc.close()
