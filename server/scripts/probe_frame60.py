import asyncio
import re

import httpx

from app.sources.tilda.client import TildaCatalogClient, gallery_urls, product_url
from app.sources.tilda.config import get_tilda_sources
from app.sources.tilda.page_images import extract_page_image_urls


async def main() -> None:
    client = TildaCatalogClient()
    for src in get_tilda_sources():
        products = await client.fetch_products(src, size=200)
        for p in products:
            title = str(p.get("title") or "")
            if "Фрейм 60" not in title:
                continue
            print("FOUND", title)
            g = gallery_urls(p)
            print("API gallery count", len(g))
            for u in g:
                print(" ", u)
            url = product_url(p, src)
            print("page", url)
            async with httpx.AsyncClient(timeout=30, follow_redirects=True) as h:
                r = await h.get(url)
            page = extract_page_image_urls(r.text)
            print("page extract count", len(page))
            li = re.findall(
                r'li_img[^:]*:\s*"?(https://static\.tildacdn\.com[^"\\]+)"?',
                r.text,
            )
            print("li_img matches unique", len(set(li)))
            allimg = re.findall(
                r"https://static\.tildacdn\.com/[a-z0-9\-_/]+\.(?:jpg|jpeg|png|webp)",
                r.text,
                re.I,
            )
            print("regex all unique", len(set(allimg)))
            for u in list(dict.fromkeys(allimg))[:15]:
                print(" ", u)
            return
    print("not found")


if __name__ == "__main__":
    asyncio.run(main())
