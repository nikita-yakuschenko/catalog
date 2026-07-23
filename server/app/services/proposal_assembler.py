"""Assemble commercial proposal HTML in catalog visual language."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any, Optional

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.core.config import settings
from app.domain.models import AssetType, HouseProject
from app.services.assembler import _asset_file_url, _font_data_uri, _pick_assets, format_area, format_price


def _chunk(items: list[Any], size: int) -> list[list[Any]]:
    return [items[i : i + size] for i in range(0, len(items), size)]


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
        assets = self._assets(project, fallback_hero=project_image_url)
        gallery_spreads = self._gallery_spreads(assets)
        package_page_num = 3 + len(gallery_spreads)

        fonts_dir = self.templates_dir / "fonts"
        context = {
            "doc": document,
            "assets": assets,
            "gallery_spreads": gallery_spreads,
            "package_page_num": package_page_num,
            "project_specs": self._specs(project),
            "generated_at": date.today().strftime("%d.%m.%Y"),
            "year": date.today().year,
            "brand": "AVGST",
            "font_gilroy_light": _font_data_uri(fonts_dir / "Gilroy-Light.otf"),
            "font_gilroy_extrabold": _font_data_uri(fonts_dir / "Gilroy-ExtraBold.otf"),
        }
        return self.env.get_template("proposals/commercial.html").render(**context)

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

            picked["gallery_exterior_urls"] = urls(secondary_ext[:6], "gallery")
            picked["gallery_interior_urls"] = urls(interiors[:6], "gallery")
            picked["gallery_detail_urls"] = urls(details[:4], "gallery")
            if not picked.get("exterior_url") and fallback_hero:
                picked["exterior_url"] = fallback_hero
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

    def _gallery_spreads(self, assets: dict[str, Any]) -> list[dict[str, Any]]:
        spreads: list[dict[str, Any]] = []
        page_num = 3

        exterior_shots = [
            {"url": u, "caption": "Экстерьер"}
            for u in (assets.get("gallery_exterior_urls") or [])
            if u
        ]
        # If no secondary exteriors, still show hero on gallery when available
        if not exterior_shots and assets.get("exterior_url"):
            # avoid duplicating cover hero unless we have nothing else
            pass

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

        def add_group(shots: list[dict[str, Any]], label: str, heading: str, sub: str) -> None:
            nonlocal page_num
            for chunk in _chunk(shots, 3):
                layout = {1: "solo", 2: "duo", 3: "trio"}[len(chunk)]
                spreads.append(
                    {
                        "label": label,
                        "heading": heading,
                        "sub": sub,
                        "shots": chunk,
                        "layout": layout,
                        "page_num": page_num,
                    }
                )
                page_num += 1

        add_group(exterior_shots, "Экстерьер", "Фасады и окружение", "Крупные ракурсы проекта")
        add_group(interior_shots, "Интерьер", "Внутреннее пространство", "Свет · объём · сценарии")
        if not exterior_shots and not interior_shots:
            add_group(detail_shots[:3], "Галерея", "Визуальный образ", "Подборка по проекту")

        return spreads
