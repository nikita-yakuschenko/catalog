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
    "итого",
    "итог",
    "опции",
    "услуги",
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

        if _is_price_line(line):
            p = _parse_price(line)
            if p is not None:
                prices.append(p)
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
            if len(title) > 2:
                options.append({"title": title, "price": price, "selected": True})

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

    options_total = sum(int(o["price"]) for o in options if o.get("selected") and o.get("price"))
    grand_total = (house_price or 0) + options_total

    client = data.get("client") or {}
    manager = data.get("manager") or {}

    return {
        "project_name": (data.get("project_name") or data.get("project") or "").strip(),
        "package_name": (data.get("package_name") or data.get("package") or "").strip() or None,
        "house_price": house_price,
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

    for key in ("package_name", "currency", "notes"):
        if incoming.get(key):
            merged[key] = incoming[key]

    # PDF estimate is source of truth for money unless API explicitly sent prices/options
    if incoming.get("house_price") and not base.get("house_price"):
        merged["house_price"] = incoming["house_price"]
    if incoming.get("options") and not base.get("options"):
        merged["options"] = incoming["options"]

    if any(incoming.get("client", {}).values()):
        merged["client"] = incoming["client"]
    if any(incoming.get("manager", {}).values()):
        merged["manager"] = incoming["manager"]
    if incoming.get("meta"):
        merged["meta"] = {**base.get("meta", {}), **incoming["meta"]}

    return normalize_document(merged)
