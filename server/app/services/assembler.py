"""Assemble catalog HTML from Jinja2 templates."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any, Optional
from uuid import UUID

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.core.config import settings
from app.domain.models import AssetType, Catalog, CatalogProject, HouseProject, Technology
from app.services.icons import ICONS
from app.services.layout_selector import LayoutSelector, layout_page_count
from app.services.qrcode_util import qr_data_uri


@dataclass
class PageEntry:
    kind: str
    title: str
    page_number: int
    project_id: Optional[UUID] = None
    technology: Optional[str] = None


@dataclass
class AssembledCatalog:
    html: str
    pages: list[PageEntry] = field(default_factory=list)
    layout_map: dict[str, str] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)


def _asset_file_url(local_path: str, *, role: str = "default") -> str:
    """Embed local images as optimized JPEG data URIs for Chromium PDF rendering."""
    path = Path(local_path)
    if not path.exists():
        return ""
    import base64

    from app.services.pdf_optimize import optimize_image_bytes

    presets = {
        "hero": (2000, 86),
        "plan": (1900, 90),
        "gallery": (1200, 84),
        "default": (1700, 85),
    }
    max_edge, quality = presets.get(role, presets["default"])
    try:
        data, mime = optimize_image_bytes(path.read_bytes(), max_edge=max_edge, quality=quality)
    except Exception:
        import mimetypes

        data = path.read_bytes()
        mime = mimetypes.guess_type(path.name)[0] or "image/jpeg"
    encoded = base64.b64encode(data).decode("ascii")
    return f"data:{mime};base64,{encoded}"


def _font_data_uri(path: Path) -> str:
    if not path.exists():
        return ""
    import base64

    data = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:font/otf;base64,{data}"


def _project_copy(project: HouseProject, custom_description: str = "") -> dict[str, str]:
    """Short marketing lines for hero / dossier (mockup-style)."""
    custom = (custom_description or "").strip()
    if custom:
        first = custom.split(".")[0].strip()
        tagline = first[:90] if first else custom[:90]
    elif project.technology == Technology.modular:
        area = project.area or 0
        tagline = (
            "Компактный дом для жизни в природе"
            if area and area <= 80
            else "Модульный дом для загородной жизни"
        )
    else:
        tagline = "Продуманный дом для постоянного проживания"

    blurb = "Продуманный формат для отдыха или постоянного проживания."
    promo = "Рациональная планировка для комфортной жизни и отдыха."
    seal = "Естественное решение для загородной жизни"
    return {
        "tagline": tagline,
        "blurb": blurb,
        "promo": promo,
        "seal": seal,
    }


def _pick_assets(project: HouseProject, selected_ids: list) -> dict[str, Any]:
    assets = [a for a in project.assets if not a.excluded]
    if selected_ids:
        idset = {str(x) for x in selected_ids}
        filtered = [a for a in assets if str(a.id) in idset]
        if filtered:
            assets = filtered
    exteriors = [a for a in assets if a.type == AssetType.exterior]
    plans = [a for a in assets if a.type == AssetType.floor_plan]
    others = [a for a in assets if a.type not in (AssetType.exterior, AssetType.floor_plan)]
    primary = next((a for a in exteriors if a.is_primary), None) or (exteriors[0] if exteriors else None)
    secondary = [a for a in exteriors if a is not primary]

    def urls(items: list, role: str = "default") -> list[str]:
        return [_asset_file_url(a.local_path, role=role) for a in items if a.local_path]

    # Only real photos for gallery — no empty slots / placeholders.
    gallery_pool = secondary + [a for a in others if a.type != AssetType.floor_plan]
    gallery_urls = [u for u in urls(gallery_pool[:3], role="gallery") if u]

    return {
        "exterior": primary,
        "exteriors": exteriors,
        "plan": plans[0] if plans else None,
        "plans": plans,
        "exterior_url": _asset_file_url(primary.local_path, role="hero") if primary and primary.local_path else "",
        "plan_url": _asset_file_url(plans[0].local_path, role="plan") if plans and plans[0].local_path else "",
        "plan_urls": urls(plans[:2], role="plan"),
        "secondary_urls": urls(secondary[:2], role="gallery"),
        "gallery_urls": gallery_urls,
        "object_position": primary.object_position if primary else "center center",
        "exterior_ratio": primary.aspect_ratio if primary else 1.78,
    }


def format_price(value: Optional[int]) -> str:
    if value is None:
        return ""
    return f"{value:,}".replace(",", " ") + " ₽"


def format_area(value: Optional[float]) -> str:
    if value is None:
        return "—"
    text = f"{value:.2f}".rstrip("0").rstrip(".").replace(".", ",")
    return f"{text} м²"


class CatalogAssembler:
    def __init__(self, templates_dir: Optional[str] = None):
        self.templates_dir = Path(templates_dir or settings.templates_dir)
        self.env = Environment(
            loader=FileSystemLoader(str(self.templates_dir)),
            autoescape=select_autoescape(["html", "xml"]),
        )
        self.env.filters["price"] = format_price
        self.env.filters["area"] = format_area
        self.selector = LayoutSelector()

    def assemble(
        self,
        catalog: Catalog,
        catalog_projects: list[CatalogProject],
        projects_by_id: dict[UUID, HouseProject],
    ) -> AssembledCatalog:
        warnings: list[str] = []
        pages: list[PageEntry] = []
        layout_map: dict[str, str] = {}
        page_num = 1
        generated_at = date.today()

        pages.append(PageEntry("cover", catalog.title, page_num))
        page_num += 1

        if catalog.show_introduction:
            pages.append(PageEntry("introduction", "О каталоге", page_num))
            page_num += 1

        if catalog.show_contents:
            pages.append(PageEntry("contents", "Содержание", page_num))
            page_num += 1

        modular = [
            cp for cp in catalog_projects if projects_by_id[cp.project_id].technology == Technology.modular
        ]
        panel = [
            cp for cp in catalog_projects if projects_by_id[cp.project_id].technology == Technology.panel
        ]
        modular.sort(key=lambda x: x.order)
        panel.sort(key=lambda x: x.order)

        toc_entries: list[dict[str, Any]] = []
        project_blocks: list[dict[str, Any]] = []
        recent_layouts: list[str] = []
        project_counter = 0

        def add_section(cps: list[CatalogProject], tech_label: str, tech_key: str, subtitle: str) -> None:
            nonlocal page_num, project_counter
            if not cps:
                return
            if catalog.show_dividers:
                pages.append(PageEntry("divider", tech_label, page_num, technology=tech_key))
                project_blocks.append(
                    {
                        "kind": "divider",
                        "title": tech_label,
                        "subtitle": subtitle,
                        "index": "01" if tech_key == "modular" else "02",
                        "page_number": page_num,
                    }
                )
                page_num += 1

            for cp in cps:
                project = projects_by_id[cp.project_id]
                layout, lw = self.selector.select(
                    project, override=cp.layout_variant_override, recent=recent_layouts
                )
                warnings.extend(lw)
                layout_map[str(project.id)] = layout
                recent_layouts.append(layout)
                if len(recent_layouts) > 3:
                    recent_layouts.pop(0)

                assets = _pick_assets(project, cp.selected_asset_ids or [])
                project_counter += 1
                title = cp.custom_title or project.short_name
                page_count = layout_page_count(layout)
                hero_page = page_num
                detail_page = page_num + 1 if page_count > 1 else page_num

                pages.append(
                    PageEntry("project", title, hero_page, project_id=project.id, technology=tech_key)
                )
                if page_count > 1:
                    pages.append(
                        PageEntry(
                            "project_detail",
                            f"{title} · планировка",
                            detail_page,
                            project_id=project.id,
                            technology=tech_key,
                        )
                    )

                toc_entries.append(
                    {
                        "title": title,
                        "page": hero_page,
                        "technology": tech_key,
                        "group": tech_label,
                    }
                )

                project_url = project.project_url or ""
                copy = _project_copy(project, cp.custom_description or "")
                project_blocks.append(
                    {
                        "kind": "project",
                        "layout": layout,
                        "project": project,
                        "title": title,
                        "project_index": project_counter,
                        "page_number": hero_page,
                        "detail_page_number": detail_page,
                        "section_label": tech_label,
                        "assets": assets,
                        "description": cp.custom_description or "",
                        "tagline": copy["tagline"],
                        "blurb": copy["blurb"],
                        "promo": copy["promo"],
                        "seal": copy["seal"],
                        "project_url": project_url,
                        "qr_url": qr_data_uri(project_url, box_size=8) if project_url else None,
                        "page_count": page_count,
                    }
                )
                page_num += page_count

        add_section(
            modular,
            "Модульные дома",
            "modular",
            f"{len(modular)} проектов заводской готовности",
        )
        add_section(
            panel,
            "Панельно-каркасные дома",
            "panel",
            f"{len(panel)} проектов для постоянного проживания",
        )

        if catalog.show_contacts:
            pages.append(PageEntry("contacts", "Контакты", page_num))
            page_num += 1

        total_pages = page_num - 1
        price_date = catalog.price_actual_at or generated_at
        modular_count = len(modular)
        panel_count = len(panel)

        fonts_dir = self.templates_dir / "fonts"
        context = {
            "catalog": catalog,
            "pages": pages,
            "toc_entries": toc_entries,
            "project_blocks": project_blocks,
            "total_pages": total_pages,
            "modular_count": modular_count,
            "panel_count": panel_count,
            "project_count": modular_count + panel_count,
            "price_actual_at": price_date.strftime("%d.%m.%Y"),
            "generated_at": generated_at.strftime("%d.%m.%Y"),
            "year": catalog.year,
            "contacts": catalog.contacts
            or {
                "site": "avgst.ru",
                "phone": "",
                "email": "",
                "address": "",
            },
            "show_prices": catalog.show_prices,
            "show_project_links": catalog.show_project_links,
            "icons": ICONS,
            "font_gilroy_light": _font_data_uri(fonts_dir / "Gilroy-Light.otf"),
            "font_gilroy_extrabold": _font_data_uri(fonts_dir / "Gilroy-ExtraBold.otf"),
        }

        template = self.env.get_template("catalog.html")
        html = template.render(**context)
        return AssembledCatalog(html=html, pages=pages, layout_map=layout_map, warnings=warnings)
