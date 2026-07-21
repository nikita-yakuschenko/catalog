import re
from app.sources.tilda.page_images import extract_page_image_urls


def test_extract_filters_chrome_and_keeps_photos():
    html = """
    https://static.tildacdn.com/tild1/logo_social_s.png
    &quot;li_img&quot;:&quot;https://static.tildacdn.com/tild1234-abcd/Barn_113__5.jpg&quot;
    https://static.tildacdn.com/tild9999/free-icon-heart-5107.png
    https://static.tildacdn.com/tild5555/photo_angle.jpg
    """
    urls = extract_page_image_urls(html, api_gallery_count=0)
    assert any("Barn_113" in u for u in urls)
    assert any("photo_angle" in u for u in urls)
    assert not any("logo" in u.lower() for u in urls)
    assert not any("heart" in u.lower() for u in urls)
