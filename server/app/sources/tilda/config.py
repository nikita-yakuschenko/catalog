"""Tilda catalog source configuration — keep store IDs out of business logic."""

from dataclasses import dataclass

from app.core.config import settings
from app.domain.models import Technology


@dataclass(frozen=True)
class TildaSource:
    key: str
    technology: Technology
    category: str
    storepartuid: str
    recid: str
    catalog_path: str


def get_tilda_sources() -> list[TildaSource]:
    return [
        TildaSource(
            key="modular",
            technology=Technology.modular,
            category="Модульные дома",
            storepartuid=settings.tilda_modular_storepartuid,
            recid=settings.tilda_modular_recid,
            catalog_path="/catalog/modulnye-doma",
        ),
        TildaSource(
            key="panel",
            technology=Technology.panel,
            category="Панельно-каркасные дома",
            storepartuid=settings.tilda_panel_storepartuid,
            recid=settings.tilda_panel_recid,
            catalog_path="/catalog/panelno-karkasnye-doma",
        ),
    ]
