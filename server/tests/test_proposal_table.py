"""Table-first KP estimate intake — title and price stay on the same row."""

from pathlib import Path

import fitz
from openpyxl import Workbook

from app.services.proposal_parse import (
    document_from_table_rows,
    is_total_label,
    parse_markdown,
)
from app.services.proposal_table import (
    extract_estimate_document,
    extract_excel_rows,
    extract_pdf_rows_pdfplumber,
    extract_pdf_rows_pymupdf,
    extract_pdf_table_rows,
)

# Смета «Барн 74» как на скрине пользователя
BARN74_ROWS = [
    ["Название проекта", "Барн 74"],
    ["Стоимость дома", 3_560_000],
    ["Допы"],
    ["Забивные сваи 150х150х3000мм", 308_000],
    ["Терраса", 359_000],
    ["Настил пола - ЦСП 10мм в 2 слоя", 138_000],
    ["Настил пола - кварцвинил", 186_000],
    ["ПВХ плинтуса", 58_000],
    ["Отделка стен - имитация бруса, сорт АВ", 191_000],
    ["Межкомнатные двери", 131_000],
    ["Натяжной потолок (без установки спот и светильников)", 88_000],
    ["Водосточная система металлическая", 87_000],
    ["Внутренняя покраска в 1 слой", 59_000],
    ["Укладка плитки на стены с/у", 330_000],
    ["Укладка плитки на пол с/у", 91_000],
    ["Аренда бытовки", 30_000],
    ["Отопление", 661_000],
    ["Вентиляция", 74_000],
    ["Водопровод и канализация", 174_000],
    ["Фаянс", 206_000],
    ["Электрика", 486_000],
    ["ИТОГО:", 7_217_000],
]

_CYR_FONT = Path(r"C:\Windows\Fonts\arial.ttf")


def _write_estimate_pdf(path: Path, rows: list[list]) -> None:
    """PDF с реальной сеткой таблицы и кириллицей (Arial)."""
    doc = fitz.open()
    page = doc.new_page(width=595, height=842)
    page.insert_font(fontname="FArial", fontfile=str(_CYR_FONT))

    x0, y0 = 36, 36
    col_w = (360, 130)
    row_h = 18
    for r, row in enumerate(rows):
        y = y0 + r * row_h
        if y + row_h > page.rect.height - 36:
            break
        left = "" if not row else str(row[0])
        right = "" if len(row) < 2 or row[1] is None else str(row[1])
        for c, (text, width) in enumerate(((left, col_w[0]), (right, col_w[1]))):
            x = x0 + (0 if c == 0 else col_w[0])
            rect = fitz.Rect(x, y, x + width, y + row_h)
            page.draw_rect(rect, color=(0, 0, 0), width=0.4)
            if text:
                page.insert_textbox(
                    fitz.Rect(x + 2, y + 2, x + width - 2, y + row_h - 2),
                    text,
                    fontname="FArial",
                    fontsize=8,
                    align=fitz.TEXT_ALIGN_LEFT if c == 0 else fitz.TEXT_ALIGN_RIGHT,
                )
    path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(path)
    doc.close()


def test_is_total_label_variants():
    assert is_total_label("ИТОГО")
    assert is_total_label("ИТОГО:")
    assert is_total_label("Всего")
    assert is_total_label("СУММА")
    assert is_total_label("Total")
    assert is_total_label("всего к оплате")
    assert not is_total_label("Терраса")
    assert not is_total_label("Забивные сваи")


def test_barn74_table_rows_match_prices():
    doc = document_from_table_rows(BARN74_ROWS)
    assert doc["project_name"] == "Барн 74"
    assert doc["house_price"] == 3_560_000
    titles = [o["title"] for o in doc["options"]]
    assert "Допы" not in titles
    assert "ИТОГО" not in titles
    assert "ИТОГО:" not in titles
    assert titles[0] == "Забивные сваи 150х150х3000мм"
    assert doc["options"][0]["price"] == 308_000
    assert titles[1] == "Терраса"
    assert doc["options"][1]["price"] == 359_000
    assert titles[-1] == "Электрика"
    assert doc["options"][-1]["price"] == 486_000
    csp = next(o for o in doc["options"] if "ЦСП" in o["title"])
    assert csp["price"] == 138_000
    assert doc["totals"]["grand"] == 7_217_000
    assert len(doc["options"]) == 18


def test_barn74_xlsx_roundtrip(tmp_path: Path):
    path = tmp_path / "barn74.xlsx"
    wb = Workbook()
    ws = wb.active
    for row in BARN74_ROWS:
        ws.append(row)
    wb.save(path)

    rows = extract_excel_rows(path)
    doc, _trace, method = extract_estimate_document(path)
    assert method == "excel"
    assert doc["project_name"] == "Барн 74"
    assert doc["house_price"] == 3_560_000
    assert doc["options"][0]["title"].startswith("Забивные сваи")
    assert doc["options"][0]["price"] == 308_000
    assert doc["totals"]["grand"] == 7_217_000
    assert len(rows) >= 20


def test_barn74_pdf_pymupdf_and_pdfplumber(tmp_path: Path):
    path = tmp_path / "barn74.pdf"
    _write_estimate_pdf(path, BARN74_ROWS)

    pymu_rows = extract_pdf_rows_pymupdf(path)
    plumber_rows = extract_pdf_rows_pdfplumber(path)
    assert len(pymu_rows) >= 5
    assert len(plumber_rows) >= 5

    for label, rows in (("pymupdf", pymu_rows), ("pdfplumber", plumber_rows)):
        doc = document_from_table_rows(rows)
        assert doc["project_name"] == "Барн 74", label
        assert doc["house_price"] == 3_560_000, label
        assert doc["options"][0]["price"] == 308_000, label
        assert doc["options"][0]["title"].startswith("Забивные сваи"), label
        csp = next(o for o in doc["options"] if "ЦСП" in o["title"])
        assert csp["price"] == 138_000, label
        assert all(o["price"] != 7_217_000 for o in doc["options"]), label
        assert doc["totals"]["grand"] == 7_217_000, label


def test_barn74_pdf_intake_uses_table_engine(tmp_path: Path):
    path = tmp_path / "barn74_intake.pdf"
    _write_estimate_pdf(path, BARN74_ROWS)

    rows, engine = extract_pdf_table_rows(path)
    assert engine in {"pdf_pymupdf", "pdf_pdfplumber"}
    assert rows

    doc, _trace, method = extract_estimate_document(path)
    assert method in {"pdf_pymupdf", "pdf_pdfplumber"}
    assert doc["project_name"] == "Барн 74"
    assert doc["house_price"] == 3_560_000
    assert doc["totals"]["grand"] == 7_217_000
    assert doc["options"][-1]["title"] == "Электрика"
    assert doc["options"][-1]["price"] == 486_000


def test_markdown_drops_itogo_sum_amount():
    """Если колонка цен включает ИТОГО=сумме строк — сумму выкидываем."""
    text = """
Барн 74
Базовая
3 560 000
308 000
359 000
138 000
7 217 000
ИТОГО:
Забивные сваи 150х150х3000мм
Терраса
Настил пола - ЦСП 10мм в 2 слоя
""".strip()
    doc = parse_markdown(text)
    assert doc["house_price"] == 3_560_000
    assert doc["totals"]["grand"] == 3_560_000 + 308_000 + 359_000 + 138_000
    assert all(o["price"] != 7_217_000 for o in doc["options"])


def test_normalize_skips_total_option_title():
    from app.services.proposal_parse import normalize_document

    doc = normalize_document(
        {
            "house_price": 1_000_000,
            "options": [
                {"title": "Терраса", "price": 100_000},
                {"title": "ИТОГО", "price": 1_100_000},
                {"title": "Всего", "price": 1_100_000},
            ],
        }
    )
    titles = [o["title"] for o in doc["options"]]
    assert titles == ["Терраса"]
    assert doc["totals"]["grand"] == 1_100_000
