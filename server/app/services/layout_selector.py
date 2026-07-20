"""Deterministic layout selection for project pages."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence

from app.domain.models import AssetType, HouseProject, ProjectAsset


@dataclass(frozen=True)
class LayoutSpec:
    id: str
    min_exterior_images: int = 1
    min_floor_plans: int = 0
    supported_floors: tuple[int, ...] = (1, 2)
    priority: int = 50
    implemented: bool = True
    pages: int = 1


LAYOUTS: dict[str, LayoutSpec] = {
    # Unified premium spread: page 1 hero, page 2 dossier
    "project_spread": LayoutSpec("project_spread", priority=100, pages=2),
    # Legacy single-page layouts kept for manual override
    "hero_plan_right": LayoutSpec("hero_plan_right", min_floor_plans=1, priority=60),
    "hero_top_plan_bottom": LayoutSpec("hero_top_plan_bottom", min_floor_plans=1, priority=50, implemented=False),
    "split_equal": LayoutSpec("split_equal", min_floor_plans=1, priority=40),
    "plan_focus": LayoutSpec("plan_focus", priority=30, implemented=False),
    "two_exteriors_plan": LayoutSpec(
        "two_exteriors_plan", min_exterior_images=2, priority=25, implemented=False
    ),
    "vertical_exterior_plan": LayoutSpec("vertical_exterior_plan", priority=20, implemented=False),
    "two_floor_plans": LayoutSpec(
        "two_floor_plans", min_floor_plans=2, supported_floors=(2,), priority=15, implemented=False
    ),
    "flagship_spread": LayoutSpec("flagship_spread", priority=10, implemented=False, pages=2),
}

IMPLEMENTED = [lid for lid, spec in LAYOUTS.items() if spec.implemented]
FALLBACK = "project_spread"


def _assets(project: HouseProject) -> list[ProjectAsset]:
    return [a for a in (project.assets or []) if not a.excluded]


def _count(assets: Sequence[ProjectAsset], typ: AssetType) -> int:
    return sum(1 for a in assets if a.type == typ)


def compatible(layout_id: str, project: HouseProject) -> bool:
    spec = LAYOUTS.get(layout_id)
    if not spec or not spec.implemented:
        return False
    assets = _assets(project)
    if _count(assets, AssetType.exterior) < spec.min_exterior_images:
        return False
    if _count(assets, AssetType.floor_plan) < spec.min_floor_plans:
        return False
    floors = project.floors or 1
    if floors not in spec.supported_floors:
        return False
    return True


def propose(project: HouseProject) -> str:
    # Unified catalog style: always two-page spread
    return "project_spread"


def layout_page_count(layout_id: str) -> int:
    spec = LAYOUTS.get(layout_id)
    return spec.pages if spec else 1


class LayoutSelector:
    """Pick layouts deterministically. Default is unified project_spread."""

    def __init__(self, max_repeat: int = 2):
        self.max_repeat = max_repeat

    def select(
        self,
        project: HouseProject,
        *,
        override: Optional[str] = None,
        recent: Optional[list[str]] = None,
    ) -> tuple[str, list[str]]:
        warnings: list[str] = []
        recent = recent or []

        if override:
            if compatible(override, project):
                return override, warnings
            warnings.append(f"Override {override} incompatible; using fallback")

        candidate = propose(project)
        if not compatible(candidate, project):
            candidate = FALLBACK
            warnings.append(f"Proposed layout incompatible; using {FALLBACK}")

        return candidate, warnings
