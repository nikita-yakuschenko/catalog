"""Assemble commercial proposal HTML."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.core.config import settings


def _price(value: int | None) -> str:
    if value is None:
        return "—"
    return f"{value:,}".replace(",", " ") + " ₽"


class ProposalAssembler:
    def __init__(self) -> None:
        self.env = Environment(
            loader=FileSystemLoader(str(Path(settings.templates_dir))),
            autoescape=select_autoescape(["html", "xml"]),
        )
        self.env.filters["price"] = _price

    def assemble(self, document: dict[str, Any], *, project_image_url: str = "") -> str:
        template = self.env.get_template("proposals/commercial.html")
        return template.render(
            doc=document,
            project_image_url=project_image_url,
            generated_at=date.today().isoformat(),
            brand="AVGST",
        )
