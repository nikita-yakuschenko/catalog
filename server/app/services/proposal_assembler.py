"""Assemble commercial proposal HTML in catalog visual language."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any, Optional

from jinja2 import Environment, FileSystemLoader, select_autoescape
from markupsafe import Markup

from app.core.config import settings
from app.domain.models import AssetType, HouseProject
from app.services.assembler import _asset_file_url, _font_data_uri, _pick_assets, format_area, format_price
from app.services.proposal_parse import normalize_document
from app.services.qrcode_util import qr_data_uri

ROOT = Path(__file__).resolve().parents[3]

# Страница с резюме (клиент/менеджер/QR) + итого: до 12 опций.
# Страница без резюме: до 15 строк таблицы (16-я обрезается в PDF).
# На 1-й странице ещё Домокомплект/Доставка/Сборка — из 15 остаётся 12 слотов под опции.
ROWS_WITH_SUMMARY = 12
ROWS_WITHOUT_SUMMARY = 15
FIXED_FIRST_ROWS = 3
FIRST_WITHOUT_SUMMARY = ROWS_WITHOUT_SUMMARY - FIXED_FIRST_ROWS  # 12


def _chunk(items: list[Any], size: int) -> list[list[Any]]:
    return [items[i : i + size] for i in range(0, len(items), size)]


def split_option_page_sizes(n: int) -> list[int]:
    """Размеры страниц опций: 1-я без резюме ≤12, промежуточные ≤15, последняя ≤12."""
    if n <= 0:
        return [0]
    if n <= ROWS_WITH_SUMMARY:
        return [n]

    sizes: list[int] = []
    remaining = n

    # Первая страница без резюме: учитываем 3 фиксированные строки
    take = min(FIRST_WITHOUT_SUMMARY, remaining - 1)
    sizes.append(take)
    remaining -= take

    while remaining > ROWS_WITH_SUMMARY:
        take = min(ROWS_WITHOUT_SUMMARY, remaining - 1)
        sizes.append(take)
        remaining -= take
    sizes.append(remaining)
    return sizes


def _load_brand_svg(name: str, templates_dir: Path) -> Markup:
    """Inline SVG for Chromium PDF — prefers templates/brand, falls back to repo root."""
    candidates = [
        templates_dir / "brand" / name,
        ROOT / name,
        ROOT / "logo.svg" if name.startswith("logo") else None,
    ]
    for path in candidates:
        if path and path.exists():
            return Markup(path.read_text(encoding="utf-8"))
    return Markup("")


class ProposalAssembler:
    def __init__(self, templates_dir: Optional[str] = None) -> None:
        self.templates_dir = Path(templates_dir or settings.templates_dir)
        self.env = Environment(
            loader=FileSystemLoader(str(self.templates_dir)),
            autoescape=select_autoescape(["html", "xml"]),
        )
        self.env.filters["price"] = format_price
        self.env.filters["area"] = format_area

    def assemble(
        self,
        document: dict[str, Any],
        *,
        project: Optional[HouseProject] = None,
        project_image_url: str = "",
    ) -> str:
        document = normalize_document(document)
        assets = self._assets(project, fallback_hero=project_image_url)
        exterior_spreads, interior_spreads = self._gallery_sections(assets)

        page_num = 2
        for spread in exterior_spreads:
            spread["page_num"] = page_num
            page_num += 1
        for spread in interior_spreads:
            spread["page_num"] = page_num
            page_num += 1
        plans_page_num = page_num
        package_pages = self._package_pages(document)
        for pkg in package_pages:
            pkg["page_num"] = page_num + 1
            page_num += 1

        fonts_dir = self.templates_dir / "fonts"
        project_url = (project.project_url or "").strip() if project else ""
        context = {
            "doc": document,
            "assets": assets,
            "exterior_spreads": exterior_spreads,
            "interior_spreads": interior_spreads,
            "plans_page_num": plans_page_num,
            "package_pages": package_pages,
            "package_page_num": package_pages[0]["page_num"] if package_pages else page_num,
            "project_specs": self._specs(project),
            "project_url": project_url,
            "qr_url": qr_data_uri(project_url, box_size=7, border=1) if project_url else None,
            "generated_at": date.today().strftime("%d.%m.%Y"),
            "year": date.today().year,
            "brand": "AVGST",
            "logo_svg": _load_brand_svg("logo.svg", self.templates_dir),
            "logo_mark_svg": _load_brand_svg("logo-mark.svg", self.templates_dir),
            "font_gilroy_light": _font_data_uri(fonts_dir / "Gilroy-Light.otf"),
            "font_gilroy_extrabold": _font_data_uri(fonts_dir / "Gilroy-ExtraBold.otf"),
        }
        return self.env.get_template("proposals/commercial.html").render(**context)

    def _package_pages(self, document: dict[str, Any]) -> list[dict[str, Any]]:
        """Split options across pages; summary/QR only on the last page."""
        options = [
            o
            for o in (document.get("options") or [])
            if o.get("selected") and o.get("price") is not None and int(o["price"]) > 0
        ]
        # Старая позиция сметы «доставка и сборка» не дублируем — логика из полей Bitrix
        filtered: list[dict[str, Any]] = []
        for opt in options:
            title = (opt.get("title") or "").strip().lower()
            if "доставка" in title and "сборк" in title:
                continue
            filtered.append(opt)
        options = filtered

        sizes = split_option_page_sizes(len(options))
        pages: list[dict[str, Any]] = []
        offset = 0
        page_count = len(sizes)
        for idx, size in enumerate(sizes):
            chunk = options[offset : offset + size]
            offset += size
            is_first = idx == 0
            is_last = idx == page_count - 1
            pages.append(
                {
                    "options": chunk,
                    "is_first": is_first,
                    "is_last": is_last,
                    "show_delivery": is_first,
                    "show_summary": is_last,
                }
            )
        return pages

    def _assets(self, project: Optional[HouseProject], *, fallback_hero: str) -> dict[str, Any]:
        if project is not None:
            picked = _pick_assets(project, [])
            # Enrich gallery with more exteriors + interiors for KP spreads
            assets = [a for a in project.assets if not a.excluded and a.local_path]
            exteriors = [a for a in assets if a.type == AssetType.exterior]
            interiors = [a for a in assets if a.type == AssetType.interior]
            details = [
                a
                for a in assets
                if a.type in (AssetType.facade, AssetType.detail, AssetType.decorative, AssetType.unknown)
            ]
            primary = next((a for a in exteriors if a.is_primary), None) or (exteriors[0] if exteriors else None)
            secondary_ext = [a for a in exteriors if a is not primary]

            def urls(items: list, role: str) -> list[str]:
                return [u for u in (_asset_file_url(a.local_path, role=role) for a in items) if u]

            # Все неисключённые ассеты: без искусственного [:6]
            picked["gallery_exterior_urls"] = urls(secondary_ext, "gallery")
            picked["gallery_interior_urls"] = urls(interiors, "gallery")
            picked["gallery_detail_urls"] = urls(details, "gallery")
            if not picked.get("exterior_url") and fallback_hero:
                picked["exterior_url"] = fallback_hero
            # КП: одна планировка на странице (дубли уже отсечены в _pick_assets)
            if picked.get("plan_urls"):
                picked["plan_urls"] = picked["plan_urls"][:1]
            return picked

        return {
            "exterior_url": fallback_hero,
            "plan_urls": [],
            "gallery_urls": [],
            "gallery_exterior_urls": [],
            "gallery_interior_urls": [],
            "gallery_detail_urls": [],
            "object_position": "center center",
        }

    def _specs(self, project: Optional[HouseProject]) -> dict[str, str]:
        if project is None:
            return {}
        return {
            "area": format_area(project.area) if project.area else "",
            "dimensions": (project.dimensions_display or "").strip(),
            "floors": str(project.floors) if project.floors else "",
            "bedrooms": str(project.bedrooms) if project.bedrooms else "",
            "bathrooms": (project.bathrooms or "").strip(),
        }

    def _gallery_sections(
        self, assets: dict[str, Any]
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        exterior_shots = [
            {"url": u, "caption": "Экстерьер"}
            for u in (assets.get("gallery_exterior_urls") or [])
            if u
        ]
        interior_shots = [
            {"url": u, "caption": "Интерьер"}
            for u in (assets.get("gallery_interior_urls") or [])
            if u
        ]
        detail_shots = [
            {"url": u, "caption": "Деталь"}
            for u in (assets.get("gallery_detail_urls") or assets.get("gallery_urls") or [])
            if u
        ]

        if not exterior_shots and detail_shots:
            exterior_shots = detail_shots

        # Фасады и интерьеры — плотная галерея (cover)
        exterior_spreads = self._spread_chunks(
            exterior_shots,
            label="Фасады",
            heading="Фасады и окружение",
            sub="Возможные варианты фасадных решений",
        )
        interior_spreads = self._spread_chunks(
            interior_shots,
            label="Интерьер",
            heading="Интерьеры",
            sub="Возможные варианты интерьерных решений",
        )
        return exterior_spreads, interior_spreads

    def _spread_chunks(
        self,
        shots: list[dict[str, Any]],
        *,
        label: str,
        heading: str,
        sub: str,
        per_page: int = 3,
    ) -> list[dict[str, Any]]:
        spreads: list[dict[str, Any]] = []
        for chunk in _chunk(shots, per_page):
            layout = {1: "solo", 2: "duo", 3: "trio"}[len(chunk)]
            spreads.append(
                {
                    "label": label,
                    "heading": heading,
                    "sub": sub,
                    "shots": chunk,
                    "layout": layout,
                }
            )
        return spreads
