from types import SimpleNamespace
from uuid import uuid4

from app.domain.models import AssetType, Technology
from app.services.layout_selector import LayoutSelector, layout_page_count, propose


def _asset(typ: AssetType, ratio: float = 1.5, primary: bool = False):
    return SimpleNamespace(
        type=typ,
        aspect_ratio=ratio,
        is_primary=primary,
        excluded=False,
        id=uuid4(),
    )


def _project(assets, floors=1):
    return SimpleNamespace(
        id=uuid4(),
        floors=floors,
        assets=assets,
        technology=Technology.modular,
        short_name="Test",
    )


def test_default_is_unified_spread():
    project = _project(
        [
            _asset(AssetType.exterior, 1.9, True),
            _asset(AssetType.floor_plan, 1.2),
        ]
    )
    assert propose(project) == "project_spread"
    assert layout_page_count("project_spread") == 2


def test_selector_override_legacy():
    selector = LayoutSelector()
    project = _project(
        [
            _asset(AssetType.exterior, 1.5, True),
            _asset(AssetType.floor_plan, 1.2),
        ]
    )
    chosen, warnings = selector.select(project, override="hero_plan_right")
    assert chosen == "hero_plan_right"
    assert warnings == []


def test_selector_default_spread():
    selector = LayoutSelector()
    project = _project([_asset(AssetType.exterior, 1.5, True)])
    a, _ = selector.select(project)
    b, _ = selector.select(project)
    assert a == b == "project_spread"
