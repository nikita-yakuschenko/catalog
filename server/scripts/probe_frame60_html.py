import asyncio
import re

import httpx

URL = "https://avgst.ru/catalog/modulnye-doma/product/frame-60"


async def main() -> None:
    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as c:
        r = await c.get(URL)
    t = r.text
    for pat in ["li_img", "gallery", "t-slds", "t-store", "slider"]:
        print(pat, t.lower().count(pat.lower()))
    stor = set(re.findall(r'"(https://static\.tildacdn\.com/stor[^"]+\.jpg)"', t))
    tild = set(re.findall(r'"(https://static\.tildacdn\.com/tild[^"]+\.jpg)"', t))
    print("stor jpg quoted", len(stor))
    print("tild jpg quoted", len(tild))
    resize = [u for u in re.findall(r"https://static\.tildacdn\.com/[^\s\"'<>]+\.jpg", t) if "resize" in u]
    print("resize urls", len(set(resize)))


if __name__ == "__main__":
    asyncio.run(main())
