"""Parse commercial proposal data from markdown or structured API payloads."""

from __future__ import annotations

import re
from typing import Any, Optional

_PRICE_RE = re.compile(r"^[\d\s\u00a0]+$")
_OPTION_PRICE_RE = re.compile(r"(\d(?:[\d\s\u00a0]{2,}\d))")
_DIM_RE = re.compile(r"\d+\s*[xх×]\s*\d+", re.IGNORECASE)
_GENERIC_TITLE_RE = re.compile(
    r"^\s*коммерческ(ое|ое)\s+предложение(\s*#?\d+)?\s*$",
    re.IGNORECASE,
)

# Section headers that MarkItDown often spills into option lists
_SKIP_OPTION_TITLES = {
    "стоимость дома",
    "домокомплект",
    "дополнительные услуги",
    "дополнительно",
    "допы",
    "допы:",
    "проект дома",
    "название проекта",
    "итого",
    "итог",
    "всего",
    "сумма",
    "опции",
    "услуги",
    "позиция",
    "стоимость",
}

# Итоговые / результирующие строки сметы — никогда не опции
_TOTAL_LABEL_RE = re.compile(
    r"^\s*(итого|итог|всего|сумма|total|grand\s*total|всего\s*к\s*оплате|"
    r"итоговая\s*стоимость|общая\s*стоимость|к\s*оплате)\b",
    re.IGNORECASE,
)

_PROJECT_LABEL_RE = re.compile(
    r"^\s*(название\s*проекта|проект|project(\s*name)?)\s*:?\s*$",
    re.IGNORECASE,
)

_HOUSE_PRICE_LABEL_RE = re.compile(
    r"^\s*(стоимость\s*дома|домокомплект|цена\s*дома|house(\s*price)?)\s*:?\s*$",
    re.IGNORECASE,
)

_REGION_NN = "Нижегородская область"
_REGION_MO = "Московская область"
_REGION_OTHER = "Другое"


def client_region_label(region: Optional[str]) -> Optional[str]:
    """В блоке «Клиент» — название региона; «Другое» и пустые/цифровые ID скрываем."""
    name = (region or "").strip()
    if not name or name.isdigit() or name.lower() == _REGION_OTHER.lower():
        return None
    return name


def _coerce_money(raw: Any) -> Optional[int]:
    if raw in (None, "", [], {}, 0, "0"):
        return None
    if isinstance(raw, (int, float)):
        amount = int(raw)
        return amount if amount > 0 else None
    text = str(raw).strip()
    if "|" in text:
        text = text.split("|", 1)[0].strip()
    text = text.replace("\u00a0", "").replace(" ", "").replace(",", ".")
    try:
        amount = int(round(float(text)))
    except ValueError:
        return None
    return amount if amount > 0 else None


def delivery_footnote_for_region(region: Optional[str]) -> str:
    """Сноска, когда отдельная цена доставки не задана."""
    name = (region or "").strip()
    if name == _REGION_NN:
        return "В стоимость включена доставка до 50 км"
    if name == _REGION_MO:
        return "Доставка включена в стоимость из расчёта до г. Ногинск Московской области."
    return "Доставка включена в стоимость."


def resolve_delivery_block(
    *,
    region: Optional[str] = None,
    delivery_price: Any = None,
) -> dict[str, Any]:
    """Цена из Bitrix → в таблицу; пусто/0 → «включена» + региональная сноска."""
    price = _coerce_money(delivery_price)
    region_name = (region or "").strip() or None
    if price:
        return {
            "region": region_name,
            "delivery_price": price,
            "delivery_included": False,
            "delivery_footnote": None,
            "assembly_included": True,
        }
    return {
        "region": region_name,
        "delivery_price": None,
        "delivery_included": True,
        "delivery_footnote": delivery_footnote_for_region(region_name),
        "assembly_included": True,
    }


def _parse_price(raw: str) -> Optional[int]:
    cleaned = raw.replace("\u00a0", " ").replace(" ", "").strip()
    if not cleaned.isdigit():
        return None
    return int(cleaned)


def _is_price_line(line: str) -> bool:
    compact = line.replace("\u00a0", " ").replace(" ", "")
    return bool(_PRICE_RE.match(line)) or (compact.isdigit() and len(compact) >= 3)


def _is_section_header(line: str) -> bool:
    return line.lower().strip(" :.—-") in _SKIP_OPTION_TITLES


def is_total_label(line: str) -> bool:
    """True for ИТОГО / ВСЕГО / СУММА and similar result rows."""
    text = (line or "").strip()
    if not text:
        return False
    if _TOTAL_LABEL_RE.match(text):
        return True
    return text.lower().strip(" :.—-") in {"итого", "итог", "всего", "сумма", "total"}


def is_project_label(line: str) -> bool:
    return bool(_PROJECT_LABEL_RE.match((line or "").strip()))


def is_house_price_label(line: str) -> bool:
    return bool(_HOUSE_PRICE_LABEL_RE.match((line or "").strip()))


def _is_generic_project_title(name: str) -> bool:
    return bool(_GENERIC_TITLE_RE.match((name or "").strip()))


def _drop_redundant_total_price(prices: list[int]) -> list[int]:
    """Убрать сумму ИТОГО, если она = дом + допы (частый артефакт колонки цен)."""
    if len(prices) < 2:
        return prices
    total = prices[-1]
    rest = sum(prices[:-1])
    if total == rest or abs(total - rest) <= 1:
        return prices[:-1]
    return prices


def document_from_table_rows(rows: list[list[Any]]) -> dict[str, Any]:
    """Собрать документ КП из строк таблицы: [название, цена] в одной строке.

    Гарантия соответствия: цена берётся только из той же строки, что и позиция.
    Строки ИТОГО/ВСЕГО и заголовки секций пропускаются целиком.
    """
    project_name = ""
    package_name: Optional[str] = None
    house_price: Optional[int] = None
    options: list[dict[str, Any]] = []

    for raw_row in rows:
        cells = [_cell_text(c) for c in raw_row]
        cells = [c for c in cells if c is not None]
        if not cells:
            continue

        left = cells[0]
        right = cells[1] if len(cells) > 1 else ""

        if is_total_label(left) or (right and is_total_label(right) and not _coerce_money(left)):
            continue

        if is_project_label(left):
            name = right or (cells[2] if len(cells) > 2 else "")
            if name and not _coerce_money(name):
                project_name = name
            continue

        if is_house_price_label(left):
            price = _coerce_money(right) or _coerce_money(left)
            if price:
                house_price = price
            continue

        # Одна ячейка-заголовок секции без цены
        if _is_section_header(left) and not _coerce_money(right):
            continue

        if is_total_label(left):
            continue

        price = _coerce_money(right)
        # Иногда MarkItDown/PDF: цена слева, текст справа — не наш формат AVGST
        if price is None and len(cells) >= 2:
            price = _coerce_money(left)
            if price and right and not _coerce_money(right):
                left, right = right, left
                price = _coerce_money(right)

        title = left.strip()
        if not title or is_total_label(title) or _is_section_header(title):
            continue

        # Строка «Название проекта | Барн 74» без явного лейбла уже обработана;
        # чисто текстовая вторая колонка без цены — имя проекта, если ещё пусто
        if price is None and right and not _coerce_money(right):
            if not project_name and left.lower().startswith("название"):
                project_name = right
            continue

        if price is not None and price > 0:
            options.append({"title": title, "price": price, "selected": True})

    # Если дом не был отдельной строкой — первая опция с крупной ценой не трогаем;
    # house_price должен прийти из «Стоимость дома» / первой цены ниже.
    return normalize_document(
        {
            "project_name": project_name,
            "package_name": package_name,
            "house_price": house_price,
            "options": options,
        }
    )


def _cell_text(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    text = str(value).replace("\u00a0", " ").strip()
    return text or None


def _extract_inline_price(line: str) -> tuple[str, Optional[int]]:
    """Pull trailing money amount from a title; ignore dimension digits like 150x3000мм."""
    if _DIM_RE.search(line) or "мм" in line.lower():
        return line, None
    m = _OPTION_PRICE_RE.search(line)
    if not m:
        return line, None
    price = _parse_price(m.group(1))
    if price is None or price < 1000:
        return line, None
    title = line.replace(m.group(1), "").strip(" -—:\t")
    return title or line, price


def parse_markdown(text: str) -> dict[str, Any]:
    """Heuristic parser for estimator PDFs (project, package, prices, options).

    MarkItDown often yields: title, package, price column, then 'Итого', then labels.
    Prefer document_from_table_rows when real tables are available.
    """
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    project_name = ""
    package_name: Optional[str] = None
    prices: list[int] = []
    options: list[dict[str, Any]] = []
    in_totals = False

    for i, line in enumerate(lines):
        if is_total_label(line):
            # Сумма ИТОГО часто уже попала в колонку цен — выкидываем её
            prices = _drop_redundant_total_price(prices)
            in_totals = True
            continue
        if in_totals and line in {"?", "✓", "✔", "•", "-", "—"}:
            continue
        if _is_section_header(line) or is_total_label(line):
            continue

        if _is_price_line(line):
            p = _parse_price(line)
            if p is not None:
                prices.append(p)
            continue

        # Явно пустая цена в смете ("-") — не сдвигает следующие суммы
        if line in {"-", "—", "–"}:
            if options and options[-1].get("price") is None:
                options[-1]["price"] = 0
            continue

        if not project_name and not _looks_like_option(line):
            project_name = line
            continue

        if package_name is None and not in_totals and len(line) < 64 and not _looks_like_option(line):
            if i < 5 and not any(ch.isdigit() for ch in line):
                package_name = line
                continue

        # Option titles usually appear after the price column / "Итого"
        if in_totals or prices:
            title, price = _extract_inline_price(line)
            if is_total_label(title) or _is_section_header(title):
                continue
            if len(title) > 2:
                options.append({"title": title, "price": price, "selected": True})

    prices = _drop_redundant_total_price(prices)
    house_price = prices[0] if prices else None
    option_prices = prices[1:] if len(prices) > 1 else []

    # Pair price-column leftovers with option titles (common MarkItDown table split)
    if options and option_prices:
        unmatched = [o for o in options if o.get("price") is None]
        for opt, pr in zip(unmatched, option_prices, strict=False):
            opt["price"] = pr
    elif not options and option_prices:
        for idx, pr in enumerate(option_prices, start=1):
            options.append({"title": f"Опция {idx}", "price": pr, "selected": True})

    # Нулевая цена (из "-") не участвует в итоге как опция с суммой
    for opt in options:
        if opt.get("price") == 0:
            opt["price"] = None

    return normalize_document(
        {
            "project_name": project_name,
            "package_name": package_name,
            "house_price": house_price,
            "options": options,
        }
    )


def _looks_like_option(line: str) -> bool:
    return len(line) > 80 or line.count("(") > 2


def normalize_document(data: dict[str, Any]) -> dict[str, Any]:
    """Canonical JSON document for templates and storage."""
    options = []
    for raw in data.get("options") or []:
        if isinstance(raw, str):
            title = raw.strip()
            if title and not _is_section_header(title) and not is_total_label(title):
                options.append({"title": title, "price": None, "selected": True})
            continue
        title = str(raw.get("title") or raw.get("name") or "").strip()
        if not title or _is_section_header(title) or is_total_label(title):
            continue
        options.append(
            {
                "title": title,
                "price": raw.get("price"),
                "selected": bool(raw.get("selected", True)),
            }
        )

    house_price = data.get("house_price")
    if house_price is not None:
        house_price = int(house_price)

    # Прочерк / без цены — не входит в состав и в сумму
    options = [
        o
        for o in options
        if o.get("selected") and o.get("price") is not None and int(o["price"]) > 0
    ]

    delivery = resolve_delivery_block(
        region=data.get("region"),
        delivery_price=data.get("delivery_price"),
    )
    options_total = sum(int(o["price"]) for o in options)
    delivery_amount = delivery["delivery_price"] or 0
    grand_total = (house_price or 0) + options_total + delivery_amount

    client = data.get("client") or {}
    manager = data.get("manager") or {}

    return {
        "project_name": (data.get("project_name") or data.get("project") or "").strip(),
        "package_name": (data.get("package_name") or data.get("package") or "").strip() or None,
        "house_price": house_price,
        "region": delivery["region"],
        "region_label": client_region_label(delivery["region"]),
        "delivery_price": delivery["delivery_price"],
        "delivery_included": delivery["delivery_included"],
        "delivery_footnote": delivery["delivery_footnote"],
        "assembly_included": True,
        "currency": data.get("currency") or "RUB",
        "options": options,
        "client": {
            "name": (client.get("name") or "").strip(),
            "company": (client.get("company") or "").strip(),
            "phone": (client.get("phone") or "").strip(),
            "email": (client.get("email") or "").strip(),
        },
        "manager": {
            "name": (manager.get("name") or "").strip(),
            "phone": (manager.get("phone") or "").strip(),
            "email": (manager.get("email") or "").strip(),
        },
        "notes": (data.get("notes") or "").strip(),
        "totals": {
            "options": options_total,
            "delivery": delivery_amount or None,
            "grand": grand_total if grand_total else None,
        },
        "meta": data.get("meta") or {},
    }


# Prefer PDF prices/options; Bitrix linked project name overrides generic titles / PDF name.
def merge_documents(structured: dict[str, Any], parsed: dict[str, Any]) -> dict[str, Any]:
    """Merge Bitrix/API fields with PDF parse.

    - project_name from База проектов (real title) wins over PDF and generic КП titles
    - house_price / options from PDF fill when Bitrix has no structured prices
    """
    base = normalize_document(parsed)
    incoming = normalize_document(structured)

    merged: dict[str, Any] = {**base}

    in_name = incoming.get("project_name") or ""
    if in_name and not _is_generic_project_title(in_name):
        merged["project_name"] = in_name
    elif base.get("project_name"):
        merged["project_name"] = base["project_name"]

    for key in ("package_name", "currency", "notes", "region"):
        if incoming.get(key):
            merged[key] = incoming[key]

    # PDF estimate is source of truth for money unless API explicitly sent prices/options
    if incoming.get("house_price") and not base.get("house_price"):
        merged["house_price"] = incoming["house_price"]
    if incoming.get("options") and not base.get("options"):
        merged["options"] = incoming["options"]

    # Стоимость доставки — поле Bitrix важнее PDF-опции «доставка и сборка»
    if "delivery_price" in structured or incoming.get("delivery_price") is not None:
        merged["delivery_price"] = incoming.get("delivery_price")
    if incoming.get("region"):
        merged["region"] = incoming["region"]

    if any(incoming.get("client", {}).values()):
        merged["client"] = incoming["client"]
    if any(incoming.get("manager", {}).values()):
        merged["manager"] = incoming["manager"]
    if incoming.get("meta"):
        merged["meta"] = {**base.get("meta", {}), **incoming["meta"]}

    return normalize_document(merged)
