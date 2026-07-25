"""Локальный PaddleOCR (CPU, русский) для сканов и изображений в intake КП."""

from __future__ import annotations

import io
import logging
import re
import threading
from pathlib import Path
from typing import Any, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

_ocr_lock = threading.Lock()
_ocr_engine: Any = None

# Латиница, которую PP-OCR путает с кириллицей внутри русских слов
_LATIN_LOOKALIKES = str.maketrans(
    {
        "A": "А",
        "a": "а",
        "B": "В",
        "E": "Е",
        "e": "е",
        "K": "К",
        "M": "М",
        "H": "Н",
        "O": "О",
        "o": "о",
        "P": "Р",
        "p": "р",
        "C": "С",
        "c": "с",
        "T": "Т",
        "X": "Х",
        "x": "х",
        "y": "у",
    }
)
_CYR_RE = re.compile(r"[А-Яа-яЁё]")
_LAT_RE = re.compile(r"[A-Za-z]")


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
            det_db_box_thresh=0.4,
            drop_score=0.4,
        )
        return _ocr_engine


def _box_y_center(box: Any) -> float:
    ys = [float(p[1]) for p in box]
    return (min(ys) + max(ys)) / 2.0


def _box_x_left(box: Any) -> float:
    return min(float(p[0]) for p in box)


def _box_height(box: Any) -> float:
    ys = [float(p[1]) for p in box]
    return max(1.0, max(ys) - min(ys))


def fix_cyrillic_lookalikes(text: str) -> str:
    """Если в токене больше кириллицы — заменить латинские lookalike на кириллицу."""
    parts: list[str] = []
    for token in re.split(r"(\s+)", text):
        if not token or token.isspace():
            parts.append(token)
            continue
        cyr = len(_CYR_RE.findall(token))
        lat = len(_LAT_RE.findall(token))
        if cyr > 0 and cyr >= lat:
            parts.append(token.translate(_LATIN_LOOKALIKES))
        else:
            parts.append(token)
    return "".join(parts)


def _blocks_from_result(result: Any, *, min_score: float = 0.45) -> list[tuple[Any, str, float]]:
    out: list[tuple[Any, str, float]] = []
    if not result:
        return out
    pages = result if isinstance(result, list) else [result]
    for page in pages:
        if not page:
            continue
        for block in page:
            if not block:
                continue
            try:
                box = block[0]
                text = str(block[1][0]).strip()
                score = float(block[1][1]) if len(block[1]) > 1 else 1.0
            except Exception:
                continue
            if not text or score < min_score:
                continue
            out.append((box, fix_cyrillic_lookalikes(text), score))
    return out


def _result_to_text(result: Any) -> str:
    """PaddleOCR → текст построчно (ячейки одной строки таблицы склеиваются)."""
    blocks = _blocks_from_result(result)
    if not blocks:
        return ""

    # Группировка в строки по Y (допуск ~ половины высоты бокса)
    items = sorted(blocks, key=lambda b: (_box_y_center(b[0]), _box_x_left(b[0])))
    rows: list[list[tuple[Any, str, float]]] = []
    for item in items:
        y = _box_y_center(item[0])
        h = _box_height(item[0])
        tol = max(12.0, h * 0.6)
        if rows:
            row_y = sum(_box_y_center(b[0]) for b in rows[-1]) / len(rows[-1])
            if abs(y - row_y) <= tol:
                rows[-1].append(item)
                continue
        rows.append([item])

    lines: list[str] = []
    for row in rows:
        row.sort(key=lambda b: _box_x_left(b[0]))
        # Две колонки сметы: название + цена → одна строка через пробелы
        line = "  ".join(t for _, t, _ in row).strip()
        if line:
            lines.append(line)
    return "\n".join(lines).strip()


def _prepare_image_array(arr):
    """RGB PIL-array → BGR + апскейл мелких картинок (таблицы сметы)."""
    import numpy as np

    if arr.ndim == 2:
        arr = np.stack([arr, arr, arr], axis=-1)
    # Paddle/OpenCV ждут BGR
    bgr = arr[:, :, ::-1].copy()
    h, w = bgr.shape[:2]
    min_side = min(h, w)
    target = 1600
    if min_side < target:
        scale = target / float(min_side)
        new_w = max(1, int(round(w * scale)))
        new_h = max(1, int(round(h * scale)))
        try:
            import cv2

            bgr = cv2.resize(bgr, (new_w, new_h), interpolation=cv2.INTER_CUBIC)
        except ImportError:
            from PIL import Image

            img = Image.fromarray(arr).resize((new_w, new_h), Image.Resampling.LANCZOS)
            rgb = np.array(img.convert("RGB"))
            bgr = rgb[:, :, ::-1].copy()
    return bgr


def ocr_image_array(image) -> str:
    """OCR numpy array → text."""
    engine = _get_engine()
    prepared = _prepare_image_array(image)
    result = engine.ocr(prepared, cls=True)
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
    # Для сканов чуть выше дефолта 200 — лучше по кириллице
    dpi = max(dpi, 220)
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
