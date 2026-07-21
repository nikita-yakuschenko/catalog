import asyncio

from app.sources.tilda.client import TildaCatalogClient, gallery_urls, product_url
from app.sources.tilda.config import get_tilda_sources
from app.sources.tilda.page_images import fetch_merged_image_urls
from app.services.assets import classify_gallery_index


async def main() -> None:
    client = TildaCatalogClient()
    src = next(iter(get_tilda_sources()))
    products = await client.fetch_products(src, size=200)
    p = next(x for x in products if "Фрейм 60" in str(x.get("title") or ""))
    api = gallery_urls(p)
    url = product_url(p, src)
    merged = await fetch_merged_image_urls(url, api)
    print("count", len(merged))
    for i, u in enumerate(merged[:12]):
        print(i, classify_gallery_index(i).value, u.split("/")[-1][:50])


if __name__ == "__main__":
    asyncio.run(main())
