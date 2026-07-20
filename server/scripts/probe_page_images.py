import asyncio
import re

import httpx
from sqlalchemy import select

from app.core.db import SessionLocal
from app.domain.models import HouseProject


async def main() -> None:
    async with SessionLocal() as session:
        result = await session.execute(select(HouseProject).limit(3))
        projects = list(result.scalars())
    async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
        for project in projects:
            url = project.project_url
            print("===", project.short_name, url)
            try:
                resp = await client.get(url)
            except Exception as exc:
                print("fetch fail", exc)
                continue
            print("status", resp.status_code, "bytes", len(resp.content))
            html = resp.text
            found = re.findall(
                r"https://static\.tildacdn\.com/[^\s\"'<>]+\.(?:jpg|jpeg|png|webp)",
                html,
                flags=re.I,
            )
            uniq: list[str] = []
            seen: set[str] = set()
            for item in found:
                if item not in seen:
                    seen.add(item)
                    uniq.append(item)
            print("images", len(uniq))
            for item in uniq[:12]:
                print(" ", item)


if __name__ == "__main__":
    asyncio.run(main())
