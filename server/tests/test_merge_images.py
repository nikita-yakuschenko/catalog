from app.sources.tilda.page_images import (
    image_dedupe_key,
    merge_project_image_urls,
    normalize_tilda_image_url,
)


def test_normalize_and_dedupe_resize_variants():
    full = "https://static.tildacdn.com/stor3661-3563/c5793a2ac07ff7ded02bce754ed545ad.jpg"
    tiny = (
        "https://static.tildacdn.com/stor3661-3563/-/resizeb/20x/"
        "c5793a2ac07ff7ded02bce754ed545ad.jpg"
    )
    assert normalize_tilda_image_url(tiny) == full
    assert image_dedupe_key(full) == image_dedupe_key(tiny)


def test_merge_prefers_api_order_and_dedupes():
    api = [
        "https://static.tildacdn.com/stor/a/exterior.jpg",
        "https://static.tildacdn.com/stor/b/plan.jpg",
    ]
    html = """
    https://static.tildacdn.com/stor/a/exterior.jpg
    https://static.tildacdn.com/stor/a/-/resizeb/20x/exterior.jpg
    https://static.tildacdn.com/tild/x/_page-0001.jpg
    li_img&quot;:&quot;https://static.tildacdn.com/tild/g/1.jpg&quot;
    li_img&quot;:&quot;https://static.tildacdn.com/tild/g/2.jpg&quot;
    """
    merged = merge_project_image_urls(api, html)
    assert merged[0].endswith("exterior.jpg")
    assert merged[1].endswith("plan.jpg")
    assert not any("_page-0001" in u for u in merged)
    assert sum(1 for u in merged if u.endswith("exterior.jpg")) == 1
    assert any(u.endswith("/1.jpg") for u in merged)
    assert any(u.endswith("/2.jpg") for u in merged)
