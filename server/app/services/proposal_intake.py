"""Convert incoming PDF / Office files for KP parsing."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def file_to_markdown(path: Path) -> str:
    """Prefer Microsoft MarkItDown; fall back to PyMuPDF plain text for PDFs."""
    path = path.resolve()
    try:
        from markitdown import MarkItDown

        result = MarkItDown().convert(str(path))
        text = (result.text_content or "").strip()
        if text:
            return text
    except Exception:
        pass

    if path.suffix.lower() != ".pdf":
        return ""

    import fitz

    doc = fitz.open(path)
    try:
        parts: list[str] = []
        for page in doc:
            parts.append(page.get_text())
        return "\n".join(parts).strip()
    finally:
        doc.close()


# Backward-compatible alias
def pdf_to_markdown(path: Path) -> str:
    return file_to_markdown(path)


def ingest_estimate_file(path: Path) -> tuple[dict[str, Any], str, str]:
    """Table-first intake: Excel/PDF rows keep title↔price; MarkItDown is fallback."""
    from app.services.proposal_table import extract_estimate_document

    return extract_estimate_document(path)
