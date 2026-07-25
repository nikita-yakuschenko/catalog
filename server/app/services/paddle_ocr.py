"""Локальный PaddleOCR (CPU, русский) для сканов и изображений в intake КП."""

from __future__ import annotations

import io
import logging
import threading
from pathlib import Path
from typing import Any, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

_ocr_lock = threading.Lock()
_ocr_engine: Any = None


class OcrError(RuntimeError):
    """OCR недоступен или не смог распознать файл."""


def _get_engine():
    global _ocr_engine
    if _ocr_engine is not None:
        return _ocr_engine
    with _ocr_lock:
        if _ocr_engine is not None:
            return _ocr_engine
        try:
            from paddleocr import PaddleOCR
        except ImportError as exc:
            raise OcrError(
                "PaddleOCR не установлен. Добавьте paddleocr/paddlepaddle в requirements."
            ) from exc
        lang = (settings.ocr_lang or "ru").strip() or "ru"
        logger.info("loading PaddleOCR lang=%s (CPU)", lang)
        _ocr_engine = PaddleOCR(
            use_angle_cls=True,
            lang=lang,
            use_gpu=False,
            show_log=False,
        )
        return _ocr_engine


def _box_sort_key(item: Any) -> tuple[float, float]:
    """Сортировка блоков: сверху вниз, слева направо."""
    try:
        box = item[0]
        ys = [float(p[1]) for p in box]
        xs = [float(p[0]) for p in box]
        return (min(ys), min(xs))
    except Exception:
        return (0.0, 0.0)


def _result_to_text(result: Any) -> str:
    """PaddleOCR result → plain text lines."""
    if not result:
        return ""
    lines: list[str] = []
    # result is list per image; each page: list of [box, (text, conf)]
    pages = result if isinstance(result, list) else [result]
    for page in pages:
        if not page:
            continue
        blocks = [b for b in page if b]
        blocks.sort(key=_box_sort_key)
        for block in blocks:
            try:
                text = str(block[1][0]).strip()
            except Exception:
                continue
            if text:
                lines.append(text)
    return "\n".join(lines).strip()


def ocr_image_array(image) -> str:
    """OCR numpy RGB/BGR array → text."""
    engine = _get_engine()
    result = engine.ocr(image, cls=True)
    return _result_to_text(result)


def ocr_image_bytes(data: bytes) -> str:
    """OCR raw image bytes (PNG/JPEG/WEBP) → markdown-ish text."""
    if not data:
        raise OcrError("Пустое изображение для OCR")
    try:
        import numpy as np
        from PIL import Image
    except ImportError as exc:
        raise OcrError("Для OCR нужны Pillow и numpy") from exc

    try:
        img = Image.open(io.BytesIO(data))
        img = img.convert("RGB")
        arr = np.array(img)
    except Exception as exc:
        raise OcrError(f"Не удалось открыть изображение: {exc}") from exc

    text = ocr_image_array(arr)
    if not text:
        raise OcrError("OCR не распознал текст на изображении")
    return text


def ocr_pdf_pages(path: Path, *, dpi: Optional[int] = None) -> str:
    """Рендер PDF через PyMuPDF → OCR каждой страницы."""
    import fitz

    path = path.resolve()
    dpi = int(dpi if dpi is not None else settings.ocr_pdf_dpi)
    scale = max(dpi, 72) / 72.0
    matrix = fitz.Matrix(scale, scale)

    doc = fitz.open(path)
    try:
        parts: list[str] = []
        for i, page in enumerate(doc):
            pix = page.get_pixmap(matrix=matrix, alpha=False)
            png = pix.tobytes("png")
            try:
                text = ocr_image_bytes(png)
            except OcrError as exc:
                logger.warning("OCR page %s failed: %s", i + 1, exc)
                continue
            if text:
                parts.append(text)
        joined = "\n\n".join(parts).strip()
        if not joined:
            raise OcrError(f"OCR не распознал текст в PDF: {path.name}")
        return joined
    finally:
        doc.close()


def warmup() -> None:
    """Прогрев моделей (Docker build / startup)."""
    if not settings.ocr_enabled:
        return
    _get_engine()
