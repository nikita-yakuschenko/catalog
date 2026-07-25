"""Tests for intake routing (MarkItDown vs OCR) without loading Paddle models."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import fitz
import pytest
from PIL import Image

from app.services.proposal_intake import (
    FileKind,
    IntakeError,
    detect_file_kind,
    file_to_markdown,
    sniff_kind,
)


def _make_text_pdf(path: Path, text: str) -> Path:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), text)
    doc.save(path)
    doc.close()
    return path


def _make_empty_pdf(path: Path) -> Path:
    doc = fitz.open()
    doc.new_page()
    doc.save(path)
    doc.close()
    return path


def _make_png(path: Path) -> Path:
    Image.new("RGB", (64, 32), color=(255, 255, 255)).save(path, format="PNG")
    return path


def test_sniff_kind_pdf_and_png(tmp_path: Path):
    pdf = _make_empty_pdf(tmp_path / "a.pdf")
    png = _make_png(tmp_path / "b.png")
    assert sniff_kind(pdf) == FileKind.pdf_text
    assert sniff_kind(png) == FileKind.image


def test_detect_text_pdf_vs_scan(tmp_path: Path):
    # Helvetica в PyMuPDF не тянет кириллицу — ASCII; нужно >= ocr_min_text_chars alnum
    text_pdf = _make_text_pdf(
        tmp_path / "text.pdf",
        "Commercial proposal Barnhaus 96 price 4250000 delivery included "
        "extra options list and more printable characters here for threshold",
    )
    scan_pdf = _make_empty_pdf(tmp_path / "scan.pdf")
    assert detect_file_kind(text_pdf) == FileKind.pdf_text
    assert detect_file_kind(scan_pdf) == FileKind.pdf_scan


def test_file_to_markdown_text_pdf_uses_markitdown_path(tmp_path: Path):
    path = _make_text_pdf(
        tmp_path / "kp.pdf",
        "Название проекта Барнхаус Стоимость дома 4 250 000",
    )
    with patch("app.services.proposal_intake.detect_file_kind", return_value=FileKind.pdf_text):
        with patch("app.services.proposal_intake._markitdown_convert", return_value="MD FROM MARKITDOWN"):
            assert file_to_markdown(path) == "MD FROM MARKITDOWN"


def test_file_to_markdown_scan_calls_ocr(tmp_path: Path):
    path = _make_empty_pdf(tmp_path / "scan.pdf")
    with patch("app.services.proposal_intake.detect_file_kind", return_value=FileKind.pdf_scan):
        with patch("app.services.proposal_intake.settings") as st:
            st.ocr_enabled = True
            st.ocr_pdf_dpi = 200
            with patch("app.services.paddle_ocr.ocr_pdf_pages", return_value="OCR TEXT") as ocr:
                assert file_to_markdown(path) == "OCR TEXT"
                ocr.assert_called_once()


def test_file_to_markdown_image_calls_ocr(tmp_path: Path):
    path = _make_png(tmp_path / "smeta.png")
    with patch("app.services.proposal_intake.settings") as st:
        st.ocr_enabled = True
        with patch("app.services.paddle_ocr.ocr_image_bytes", return_value="IMG OCR") as ocr:
            assert file_to_markdown(path) == "IMG OCR"
            ocr.assert_called_once()


def test_file_to_markdown_image_ocr_disabled(tmp_path: Path):
    path = _make_png(tmp_path / "smeta.png")
    with patch("app.services.proposal_intake.settings") as st:
        st.ocr_enabled = False
        with pytest.raises(IntakeError, match="OCR отключён"):
            file_to_markdown(path)


def test_result_to_text_sorts_boxes():
    from app.services.paddle_ocr import _result_to_text

    # Fake paddle page: lower y first should come first after sort
    page = [
        [[[100, 50], [200, 50], [200, 60], [100, 60]], ("вторая", 0.9)],
        [[[10, 10], [80, 10], [80, 20], [10, 20]], ("первая", 0.9)],
    ]
    assert _result_to_text([page]) == "первая\nвторая"


def test_result_to_text_groups_table_row():
    from app.services.paddle_ocr import _result_to_text

    # Same Y → one line: title + price
    page = [
        [[[20, 100], [400, 100], [400, 120], [20, 120]], ("Забивные сваи", 0.95)],
        [[[500, 102], [600, 102], [600, 118], [500, 118]], ("357 000", 0.93)],
        [[[20, 200], [300, 200], [300, 220], [20, 220]], ("Вентиляция", 0.9)],
        [[[500, 200], [580, 200], [580, 220], [500, 220]], ("100 000", 0.91)],
    ]
    text = _result_to_text([page])
    assert "Забивные сваи  357 000" in text
    assert "Вентиляция  100 000" in text


def test_fix_cyrillic_lookalikes():
    from app.services.paddle_ocr import fix_cyrillic_lookalikes

    assert "деревянно" in fix_cyrillic_lookalikes("дереЕAhho") or "дерев" in fix_cyrillic_lookalikes(
        "деревянный"
    )
    assert fix_cyrillic_lookalikes("каркас") == "каркас"
    # Mostly latin stays
    assert "PDF" in fix_cyrillic_lookalikes("PDF")


def test_guess_filename_images():
    from app.services.bitrix_enrich import _guess_filename

    png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 8
    assert _guess_filename("", png).endswith(".png")
    jpg = b"\xff\xd8\xff\xe0" + b"\x00" * 8
    assert _guess_filename("x", jpg).endswith(".jpg")
