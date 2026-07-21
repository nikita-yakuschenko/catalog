"""Parse commercial proposal data from markdown or structured API payloads."""

from __future__ import annotations

import re
from typing import Any, Optional

_PRICE_RE = re.compile(r"^[\d\s]+$")
_OPTION_PRICE_RE = re.compile(r"(\d[\d\s]{3,})")


def _parse_price(raw: str) -> Optional[int]:
    cleaned = raw.replace("\u00a0", " ").replace(" ", "").strip()
    if not cleaned.isdigit():
        return None
    return int(cleaned)


def parse_markdown(text: str) -> dict[str, Any]:
    """Heuristic parser for estimator PDFs (project, package, prices, options)."""
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    project_name = ""
    package_name: Optional[str] = None
    prices: list[int] = []
    options: list[dict[str, Any]] = []
    in_totals = False

    for i, line in enumerate(lines):
        low = line.lower()
        if low.startswith("итого"):
            in_totals = True
            continue
        if in_totals and line in {"?", "✓", "✔", "•", "-"}:
            continue

        if _PRICE_RE.match(line.replace(" ", "")) or _OPTION_PRICE_RE.fullmatch(line.replace(" ", "")):
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

        if in_totals and len(line) > 3:
            price = None
            title = line
            m = _OPTION_PRICE_RE.search(line)
            if m:
                price = _parse_price(m.group(1))
                title = line.replace(m.group(1), "").strip(" -—:\t")
            options.append({"title": title, "price": price, "selected": True})

    house_price = prices[0] if prices else None
    option_prices = prices[1:] if len(prices) > 1 else []

    # Pair orphan prices with options when counts match
    if options and option_prices and len(options) == len(option_prices):
        for opt, pr in zip(options, option_prices, strict=False):
            if opt.get("price") is None:
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
            options.append({"title": raw, "price": None, "selected": True})
            continue
        options.append(
            {
                "title": str(raw.get("title") or raw.get("name") or "").strip(),
                "price": raw.get("price"),
                "selected": bool(raw.get("selected", True)),
            }
        )
    options = [o for o in options if o["title"]]

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


def merge_documents(structured: dict[str, Any], parsed: dict[str, Any]) -> dict[str, Any]:
    """Structured API/Bitrix fields override; PDF parse fills gaps."""
    base = normalize_document(parsed)
    incoming = normalize_document(structured)

    merged: dict[str, Any] = {**base}
    for key in (
        "project_name",
        "package_name",
        "house_price",
        "currency",
        "notes",
    ):
        if incoming.get(key):
            merged[key] = incoming[key]

    if incoming.get("options"):
        merged["options"] = incoming["options"]
    if any(incoming.get("client", {}).values()):
        merged["client"] = incoming["client"]
    if any(incoming.get("manager", {}).values()):
        merged["manager"] = incoming["manager"]
    if incoming.get("meta"):
        merged["meta"] = {**base.get("meta", {}), **incoming["meta"]}

    return normalize_document(merged)
