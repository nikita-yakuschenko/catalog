"""Convert incoming PDF / files to markdown for parsing."""

from __future__ import annotations

from pathlib import Path


def pdf_to_markdown(path: Path) -> str:
    """Prefer Microsoft MarkItDown; fall back to PyMuPDF plain text."""
    path = path.resolve()
    try:
        from markitdown import MarkItDown

        result = MarkItDown().convert(str(path))
        text = (result.text_content or "").strip()
        if text:
            return text
    except Exception:
        pass

    import fitz

    doc = fitz.open(path)
    try:
        parts: list[str] = []
        for page in doc:
            parts.append(page.get_text())
        return "\n".join(parts).strip()
    finally:
        doc.close()
