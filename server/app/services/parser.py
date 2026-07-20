"""Parse house characteristics from Tilda text/HTML descriptions."""

from __future__ import annotations

import html
import re
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ParsedCharacteristics:
    area: Optional[float] = None
    width: Optional[float] = None
    depth: Optional[float] = None
    dimensions_display: Optional[str] = None
    floors: Optional[int] = None
    bedrooms: Optional[int] = None
    bathrooms: Optional[str] = None
    raw_text: str = ""
    unmatched: list[str] = field(default_factory=list)


def strip_html(value: str) -> str:
    text = html.unescape(value or "")
    text = re.sub(r"<sup>\s*2\s*</sup>", "²", text, flags=re.I)
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.I)
    text = re.sub(r"</p\s*>", "\n", text, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n+", "\n", text)
    return text.strip()


def _to_float(raw: str) -> float:
    return float(raw.replace(",", ".").replace(" ", ""))


def parse_characteristics(*chunks: str) -> ParsedCharacteristics:
    raw = "\n".join(strip_html(c) for c in chunks if c)
    result = ParsedCharacteristics(raw_text=raw)
    if not raw:
        return result

    area_match = re.search(
        r"(?:площад[ьюяе]\s*)?(\d+(?:[.,]\d+)?)\s*(?:м(?:\s*[²2]|<sup>\s*2\s*</sup>)|м2|кв\.?\s*м)",
        raw,
        re.I,
    )
    if not area_match:
        area_match = re.search(r"(\d+(?:[.,]\d+)?)\s*м[²2]", raw, re.I)
    if area_match:
        result.area = _to_float(area_match.group(1))

    dim_match = re.search(
        r"(?:размер(?:ы)?(?:\s+дома)?\s*:?\s*)?"
        r"(\d+(?:[.,]\d+)?)\s*[xх×]\s*(\d+(?:[.,]\d+)?)\s*м?",
        raw,
        re.I,
    )
    if dim_match:
        a = _to_float(dim_match.group(1))
        b = _to_float(dim_match.group(2))
        # Convention in sample catalog: length × width (larger first often length)
        result.width = a
        result.depth = b
        result.dimensions_display = f"{_fmt(a)}×{_fmt(b)} м"

    floors_match = re.search(r"(?:этаж(?:ей|ность|а|и)?|floors?)\s*:?\s*(\d+)", raw, re.I)
    if floors_match:
        result.floors = int(floors_match.group(1))
    elif re.search(r"двухэтаж", raw, re.I):
        result.floors = 2
    elif re.search(r"одноэтаж", raw, re.I):
        result.floors = 1

    bed_match = re.search(
        r"(?:кол-?во\s+)?(?:спальн(?:и|я|ен)|спален|bedroom(?:s)?)\s*:?\s*(\d+)",
        raw,
        re.I,
    )
    if bed_match:
        result.bedrooms = int(bed_match.group(1))

    bath_match = re.search(
        r"(?:кол-?во\s+)?(?:с/?у|санузл(?:ов|а|ы)?|bathroom(?:s)?)\s*:?\s*([\d\-–]+)",
        raw,
        re.I,
    )
    if bath_match:
        result.bathrooms = bath_match.group(1).replace("–", "-")

    return result


def _fmt(value: float) -> str:
    if value == int(value):
        return f"{int(value)}"
    return f"{value:.2f}".rstrip("0").rstrip(".").replace(".", ",")


def short_name_from_title(title: str) -> str:
    """Strip technology prefixes: 'Модульный дом Барнхаус 90' -> 'Барнхаус 90'."""
    name = strip_html(title)
    name = re.sub(
        r"^(модульный\s+дом|панельно[-\s]?каркасный\s+дом|каркасный\s+дом)\s+",
        "",
        name,
        flags=re.I,
    )
    return name.strip() or title


def slugify(value: str) -> str:
    table = {
        "а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "e",
        "ж": "zh", "з": "z", "и": "i", "й": "y", "к": "k", "л": "l", "м": "m",
        "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u",
        "ф": "f", "х": "h", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "sch",
        "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya",
    }
    value = value.lower().strip()
    out = []
    for ch in value:
        if ch in table:
            out.append(table[ch])
        elif ch.isalnum():
            out.append(ch)
        elif ch in (" ", "-", "_"):
            out.append("-")
    slug = re.sub(r"-+", "-", "".join(out)).strip("-")
    return slug or "project"
