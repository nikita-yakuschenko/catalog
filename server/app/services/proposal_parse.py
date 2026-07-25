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
    "дополнительные услуги",
    "дополнительно",
    "проект дома",
    "название проекта",
    "итого",
    "итог",
    "опции",
    "услуги",
    "позиция",
    "стоимость",
}

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


def _is_generic_project_title(name: str) -> bool:
    return bool(_GENERIC_TITLE_RE.match((name or "").strip()))


def _extract_inline_price(line: str) -> tuple[str, Optional[int]]:
    """Pull trailing money amount from a title; ignore dimension digits like 150x3000мм."""
    # OCR-таблица: «…150х150х3000мм  357 000» — цена в конце, размеры не трогаем
    m_all = list(_OPTION_PRICE_RE.finditer(line))
    if not m_all:
        return line, None

    price = None
    match = None
    for m in reversed(m_all):
        candidate = _parse_price(m.group(1))
        if candidate is None or candidate < 1000:
            continue
        after = line[m.end() :].strip().lower()
        before = line[: m.start()]
        if after.startswith("мм") or after.startswith("m"):
            continue
        if before.rstrip().endswith(("x", "х", "×")):
            continue
        # Размерность без пробелов «150х3000» — сам match не должен быть куском mm-блока
        window = line[max(0, m.start() - 1) : m.end() + 2]
        if re.search(r"[xх×]\s*$", before.rstrip()) or re.match(r"^\s*[xх×]", after):
            continue
        if "мм" in window.lower() and candidate < 100_000 and " " not in m.group(1).strip():
            # одиночное «3000» внутри «3000мм»
            if re.search(rf"{re.escape(m.group(1).strip())}\s*мм", line, re.I):
                continue
        price = candidate
        match = m
        break

    if price is None or match is None:
        return line, None
    title = (line[: match.start()] + line[match.end() :]).strip(" -—:\t")
    title = re.sub(r"\s{2,}", " ", title).strip()
    return title or line, price


def parse_markdown(text: str) -> dict[str, Any]:
    """Heuristic parser for estimator PDFs / OCR tables.

    MarkItDown: title, package, price column, then 'Итого', then labels.
    OCR tables: row-grouped lines like 'Забивные сваи …  357 000'.
    """
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    project_name = ""
    package_name: Optional[str] = None
    prices: list[int] = []
    options: list[dict[str, Any]] = []
    in_totals = False

    for i, line in enumerate(lines):
        low = line.lower().strip(" :")
        if low.startswith("итого") or low.startswith("итог"):
            in_totals = True
            continue
        if in_totals and line in {"?", "✓", "✔", "•", "-", "—"}:
            continue
        if _is_section_header(line):
            continue

        # OCR header rows
        if low.startswith("название проекта"):
            rest = re.sub(r"(?i)^название проекта\s*:?\s*", "", line).strip(" -—:\t")
            if rest and not _is_price_line(rest):
                project_name = rest
            continue
        if low.startswith("стоимость дома"):
            _, price = _extract_inline_price(line)
            if price is None:
                tail = re.sub(r"(?i)^стоимость дома\s*:?\s*", "", line).strip()
                price = _parse_price(tail) if _is_price_line(tail) else None
            if price is not None:
                prices = [price] + [p for p in prices if p != price]
            continue

        if _is_price_line(line):
            p = _parse_price(line)
            if p is not None:
                prices.append(p)
            continue

        if line in {"-", "—", "–"}:
            if options and options[-1].get("price") is None:
                options[-1]["price"] = 0
            continue

        # OCR: title + price on one line
        title, inline_price = _extract_inline_price(line)
        if (
            inline_price is not None
            and len(title) > 2
            and title.lower().strip(" :.—-") not in _SKIP_OPTION_TITLES
        ):
            options.append({"title": title, "price": inline_price, "selected": True})
            continue

        if not project_name and not _looks_like_option(line):
            project_name = line
            continue

        if package_name is None and not in_totals and len(line) < 64 and not _looks_like_option(line):
            if i < 5 and not any(ch.isdigit() for ch in line):
                package_name = line
                continue

        if in_totals or prices:
            title2, price2 = _extract_inline_price(line)
            if len(title2) > 2:
                options.append({"title": title2, "price": price2, "selected": True})

    house_price = prices[0] if prices else None
    option_prices = prices[1:] if len(prices) > 1 else []

    if options and option_prices:
        unmatched = [o for o in options if o.get("price") is None]
        for opt, pr in zip(unmatched, option_prices, strict=False):
            opt["price"] = pr
    elif not options and option_prices:
        for idx, pr in enumerate(option_prices, start=1):
            options.append({"title": f"Опция {idx}", "price": pr, "selected": True})

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
            if title and not _is_section_header(title):
                options.append({"title": title, "price": None, "selected": True})
            continue
        title = str(raw.get("title") or raw.get("name") or "").strip()
        if not title or _is_section_header(title):
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
