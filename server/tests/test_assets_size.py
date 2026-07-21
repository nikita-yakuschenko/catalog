from app.services.assets import asset_meets_min_size


def test_asset_meets_min_size():
    assert asset_meets_min_size(1280, 960, min_edge=128)
    assert not asset_meets_min_size(20, 14, min_edge=128)
    assert not asset_meets_min_size(200, 50, min_edge=128)
