"""Synchronize house projects from Tilda into the database."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.domain.models import AssetType, HouseProject, ProjectAsset, Technology
from app.domain.schemas import SyncResult
from app.services.assets import ensure_asset
from app.services.parser import parse_characteristics, short_name_from_title, slugify
from app.sources.tilda.client import (
    TildaCatalogClient,
    gallery_urls,
    product_price,
    product_uid,
    product_url,
)
from app.sources.tilda.config import TildaSource, get_tilda_sources
from app.sources.tilda.page_images import fetch_merged_image_urls


def _text_blob(product: dict[str, Any]) -> list[str]:
    chunks: list[str] = []
    for key in ("title", "descr", "text", "description", "characteristics", "params"):
        val = product.get(key)
        if isinstance(val, str):
            chunks.append(val)
        elif isinstance(val, list):
            for item in val:
                if isinstance(item, str):
                    chunks.append(item)
                elif isinstance(item, dict):
                    chunks.append(" ".join(str(v) for v in item.values()))
    editions = product.get("editions") or product.get("parts") or []
    if isinstance(editions, list):
        for ed in editions:
            if isinstance(ed, dict):
                for key in ("title", "descr", "text"):
                    if isinstance(ed.get(key), str):
                        chunks.append(ed[key])
    return chunks


async def sync_projects(
    session: AsyncSession,
    *,
    download_assets: bool = True,
    client: Optional[TildaCatalogClient] = None,
) -> SyncResult:
    client = client or TildaCatalogClient()
    created = updated = assets_downloaded = 0
    modular_count = panel_count = 0
    errors: list[str] = []

    for source in get_tilda_sources():
        try:
            products = await client.fetch_products(source)
        except Exception as exc:
            errors.append(f"{source.key}: fetch failed: {exc}")
            continue

        if source.technology == Technology.modular:
            modular_count = len(products)
        else:
            panel_count = len(products)

        for product in products:
            try:
                c, u, a = await _upsert_product(session, source, product, download_assets)
                created += c
                updated += u
                assets_downloaded += a
                await session.commit()
            except Exception as exc:
                await session.rollback()
                uid = product_uid(product)
                errors.append(f"{source.key}/{uid}: {exc}")

    return SyncResult(
        modular_count=modular_count,
        panel_count=panel_count,
        created=created,
        updated=updated,
        assets_downloaded=assets_downloaded,
        errors=errors,
    )


async def _upsert_product(
    session: AsyncSession,
    source: TildaSource,
    product: dict[str, Any],
    download_assets: bool,
) -> tuple[int, int, int]:
    uid = product_uid(product)
    title = str(product.get("title") or product.get("name") or f"Проект {uid}")
    short = short_name_from_title(title)
    parsed = parse_characteristics(*_text_blob(product))
    price = product_price(product)
    url = product_url(product, source)
    sort_order = int(product.get("sort") or product.get("sort_order") or 0)

    result = await session.execute(
        select(HouseProject).where(HouseProject.source == "tilda", HouseProject.source_uid == uid)
    )
    project = result.scalar_one_or_none()
    created = updated = 0
    now = datetime.now(timezone.utc)

    if project is None:
        project = HouseProject(
            source="tilda",
            source_uid=uid,
            technology=source.technology,
            category=source.category,
            name=title,
            short_name=short,
            slug=slugify(f"{source.key}-{short}"),
            features=[],
            source_payload=product,
            description="",
            currency="RUB",
            project_url="",
            sort_order=0,
            active=True,
        )
        session.add(project)
        created = 1
    else:
        updated = 1

    project.technology = source.technology
    project.category = source.category
    project.name = title
    project.short_name = short
    project.slug = slugify(f"{source.key}-{short}")
    project.area = parsed.area
    project.dimensions_width = parsed.width
    project.dimensions_depth = parsed.depth
    project.dimensions_display = parsed.dimensions_display
    project.floors = parsed.floors or project.floors or 1
    project.bedrooms = parsed.bedrooms
    project.bathrooms = parsed.bathrooms
    project.price = price
    project.description = parsed.raw_text[:4000]
    project.project_url = url
    project.sort_order = sort_order
    project.active = True
    project.source_payload = product
    project.last_synced_at = now

    await session.flush()

    assets_count = 0
    if download_assets:
        urls = gallery_urls(product)
        try:
            urls = await fetch_merged_image_urls(url, urls)
        except Exception:
            urls = urls[: settings.max_sync_assets_per_project]

        project_dir = Path(settings.storage_dir) / "projects" / str(project.id)

        # Download outside of autoflush pressure
        downloaded: list[dict] = []
        with session.no_autoflush:
            for idx, img_url in enumerate(urls):
                meta = await ensure_asset(img_url, project_dir, idx)
                if meta is None:
                    continue
                downloaded.append(meta)

        assets_result = await session.execute(
            select(ProjectAsset).where(ProjectAsset.project_id == project.id)
        )
        existing_assets = list(assets_result.scalars().all())
        existing_by_url = {a.source_url: a for a in existing_assets}
        keep_urls = {m["source_url"] for m in downloaded}
        for asset in existing_assets:
            if asset.source_url not in keep_urls:
                await session.delete(asset)

        for meta in downloaded:
            assets_count += 1
            existing = existing_by_url.get(meta["source_url"])
            if existing:
                existing.local_path = meta["local_path"]
                existing.mime_type = meta["mime_type"]
                existing.width = meta["width"]
                existing.height = meta["height"]
                existing.aspect_ratio = meta["aspect_ratio"]
                existing.file_size = meta["file_size"]
                existing.dpi = meta["dpi"]
                existing.checksum = meta["checksum"]
                existing.quality_status = meta["quality_status"]
                existing.sort_order = meta["sort_order"]
                if existing.type == AssetType.unknown and meta["type"] != AssetType.unknown:
                    existing.type = meta["type"]
                if existing.type == AssetType.exterior:
                    existing.is_primary = meta["is_primary"]
            else:
                session.add(
                    ProjectAsset(
                        project_id=project.id,
                        type=meta["type"],
                        source_url=meta["source_url"],
                        local_path=meta["local_path"],
                        mime_type=meta["mime_type"],
                        width=meta["width"],
                        height=meta["height"],
                        aspect_ratio=meta["aspect_ratio"],
                        file_size=meta["file_size"],
                        dpi=meta["dpi"],
                        sort_order=meta["sort_order"],
                        is_primary=meta["is_primary"],
                        quality_status=meta["quality_status"],
                        checksum=meta["checksum"],
                        excluded=False,
                        object_position="center center",
                    )
                )

    return created, updated, assets_count
