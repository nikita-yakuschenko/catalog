import asyncio
import re

import httpx

from app.sources.tilda.page_images import extract_page_image_urls

URL = "https://avgst.ru/catalog/modulnye-doma/product/frame-60"

# Tilda product slider stores full-size URLs in li_img fields (often HTML-escaped JSON)
_LI_IMG_URL_RE = re.compile(
    r"li_img(?:\\)?(?:&quot;|\"|:)\s*(?:\\)?(?:&quot;|\"|:)\s*(https://static\.tildacdn\.com/[^\"\\&]+)",
    re.I,
)
_LI_IMG_SIMPLE = re.compile(
    r"li_img[^h]*(https://static\.tildacdn\.com/[a-z0-9\-_/]+\.(?:jpg|jpeg|png|webp))",
    re.I,
)


def extract_li_img_urls(page_html: str) -> list[str]:
    urls: list[str] = []
    for pat in (_LI_IMG_URL_RE, _LI_IMG_SIMPLE):
        for m in pat.finditer(page_html):
            urls.append(m.group(1).split("&quot;")[0].strip())
    seen: set[str] = set()
    out: list[str] = []
    for u in urls:
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out


async def main() -> None:
    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as c:
        r = await c.get(URL)
    t = r.text
    li = extract_li_img_urls(t)
    generic = extract_page_image_urls(t)
    print("li_img extract", len(li))
    for u in li[:20]:
        print(" ", u)
    print("generic extract", len(generic))
    print("in li not generic", len(set(li) - set(generic)))


if __name__ == "__main__":
    asyncio.run(main())
