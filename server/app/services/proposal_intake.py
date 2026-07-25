"""Convert incoming PDF / images to markdown for parsing."""

from __future__ import annotations

import logging
import re
from enum import Enum
from pathlib import Path

from app.core.config import settings

logger = logging.getLogger(__name__)

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp"}
INTAKE_EXTS = {".pdf"} | IMAGE_EXTS

_ALNUM_RE = re.compile(r"[\wА-Яа-яЁё]", re.UNICODE)


class FileKind(str, Enum):
    pdf_text = "pdf_text"
    pdf_scan = "pdf_scan"
    image = "image"
    unknown = "unknown"


class IntakeError(RuntimeError):
    """Не удалось преобразовать входной файл в текст."""


def sniff_kind(path: Path, head: bytes | None = None) -> FileKind:
    """Определить тип файла по magic bytes и суффиксу."""
    path = Path(path)
    suffix = path.suffix.lower()
    data = head
    if data is None:
        try:
            with path.open("rb") as f:
                data = f.read(32)
        except OSError:
            data = b""

    if data.startswith(b"%PDF") or suffix == ".pdf":
        # Уточнение text vs scan — отдельно через extract
        return FileKind.pdf_text  # provisional; refine in detect_file_kind

    if data.startswith(b"\x89PNG") or suffix == ".png":
        return FileKind.image
    if data[:3] == b"\xff\xd8\xff" or suffix in {".jpg", ".jpeg"}:
        return FileKind.image
    if data.startswith(b"RIFF") and b"WEBP" in data[:16]:
        return FileKind.image
    if suffix == ".webp":
        return FileKind.image

    if suffix in IMAGE_EXTS:
        return FileKind.image
    return FileKind.unknown


def _meaningful_char_count(text: str) -> int:
    return len(_ALNUM_RE.findall(text or ""))


def pdf_embedded_text(path: Path) -> str:
    """Сырой текстовый слой PDF (PyMuPDF)."""
    import fitz

    doc = fitz.open(path)
    try:
        parts: list[str] = []
        for page in doc:
            parts.append(page.get_text() or "")
        return "\n".join(parts).strip()
    finally:
        doc.close()


def detect_file_kind(path: Path) -> FileKind:
    """Фактический вид входа: text PDF / scan PDF / image."""
    path = Path(path).resolve()
    provisional = sniff_kind(path)
    if provisional == FileKind.image:
        return FileKind.image
    if provisional == FileKind.unknown and path.suffix.lower() not in {".pdf"}:
        # Попробуем как PDF если magic совпал при чтении
        with path.open("rb") as f:
            head = f.read(5)
        if not head.startswith(b"%PDF"):
            return FileKind.unknown

    text = pdf_embedded_text(path)
    if _meaningful_char_count(text) >= int(settings.ocr_min_text_chars):
        return FileKind.pdf_text
    return FileKind.pdf_scan


def _markitdown_convert(path: Path) -> str:
    try:
        from markitdown import MarkItDown

        result = MarkItDown().convert(str(path))
        return (result.text_content or "").strip()
    except Exception as exc:
        logger.warning("MarkItDown failed for %s: %s", path.name, exc)
        return ""


def _pdf_text_pipeline(path: Path) -> str:
    text = _markitdown_convert(path)
    if text:
        return text
    return pdf_embedded_text(path)


def _require_ocr() -> None:
    if not settings.ocr_enabled:
        raise IntakeError("OCR отключён (OCR_ENABLED=false), сканы/изображения не обрабатываются")


def file_to_markdown(path: Path) -> str:
    """Единый intake: PDF (текст/скан) или PNG/JPG/WEBP → markdown/текст для parse_markdown."""
    path = Path(path).resolve()
    if not path.is_file():
        raise IntakeError(f"Файл не найден: {path}")

    kind = detect_file_kind(path)
    logger.info("intake kind=%s file=%s", kind.value, path.name)

    if kind == FileKind.unknown:
        raise IntakeError(
            f"Неподдерживаемый тип файла: {path.name}. "
            f"Ожидаются PDF, PNG, JPG, JPEG, WEBP."
        )

    if kind == FileKind.pdf_text:
        text = _pdf_text_pipeline(path)
        if text:
            return text
        # Текстовый слой пропал после MarkItDown — попробуем OCR если включён
        if settings.ocr_enabled:
            logger.info("text PDF empty after MarkItDown/fitz, falling back to OCR")
            _require_ocr()
            from app.services.paddle_ocr import ocr_pdf_pages

            return ocr_pdf_pages(path, dpi=settings.ocr_pdf_dpi)
        raise IntakeError(f"Не удалось извлечь текст из PDF: {path.name}")

    if kind == FileKind.pdf_scan:
        _require_ocr()
        from app.services.paddle_ocr import ocr_pdf_pages

        return ocr_pdf_pages(path, dpi=settings.ocr_pdf_dpi)

    # image
    _require_ocr()
    from app.services.paddle_ocr import ocr_image_bytes

    data = path.read_bytes()
    return ocr_image_bytes(data)


def pdf_to_markdown(path: Path) -> str:
    """Обратная совместимость: тот же pipeline, что file_to_markdown."""
    return file_to_markdown(path)
