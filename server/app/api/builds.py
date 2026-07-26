from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.access import can_access_catalog
from app.core.auth import require_user
from app.core.config import settings
from app.core.db import get_db
from app.domain.models import Build, Catalog
from app.domain.schemas import BuildOut

router = APIRouter(dependencies=[Depends(require_user)])


def _preview_urls(build: Build) -> list[str]:
    preview = Path(build.preview_dir)
    pages = sorted(p.name for p in preview.glob("page-*.jpg"))
    urls: list[str] = []
    for name in pages:
        full = preview / name
        try:
            rel = full.resolve().relative_to(Path(settings.output_dir).resolve())
            urls.append(f"/output/{rel.as_posix()}")
        except Exception:
            urls.append(str(full))
    return urls


async def _catalog_for_user(db: AsyncSession, catalog_id: UUID, user: dict) -> Catalog:
    result = await db.execute(select(Catalog).where(Catalog.id == catalog_id))
    catalog = result.scalar_one_or_none()
    if not catalog or not can_access_catalog(catalog, user):
        raise HTTPException(404, "Каталог не найден")
    return catalog


async def _build_for_user(db: AsyncSession, build_id: UUID, user: dict) -> Build:
    result = await db.execute(select(Build).where(Build.id == build_id))
    build = result.scalar_one_or_none()
    if not build:
        raise HTTPException(404, "Сборка не найдена")
    await _catalog_for_user(db, build.catalog_id, user)
    return build


@router.get("/builds/{build_id}", response_model=BuildOut)
async def get_build(
    build_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_user),
) -> Build:
    return await _build_for_user(db, build_id, user)


@router.get("/builds/{build_id}/log")
async def get_build_log(
    build_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_user),
) -> dict:
    build = await _build_for_user(db, build_id, user)
    return {"log": build.log, "stage": build.stage, "status": build.status}


@router.get("/builds/{build_id}/pdf")
async def download_build_pdf(
    build_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_user),
):
    build = await _build_for_user(db, build_id, user)
    if not build.pdf_path or not Path(build.pdf_path).exists():
        raise HTTPException(404, "PDF не найден")
    return FileResponse(build.pdf_path, media_type="application/pdf", filename="avgst-catalog.pdf")


@router.get("/catalogs/{catalog_id}/download")
async def download_catalog_pdf(
    catalog_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_user),
):
    await _catalog_for_user(db, catalog_id, user)
    result = await db.execute(
        select(Build).where(Build.catalog_id == catalog_id).order_by(Build.created_at.desc())
    )
    build = result.scalars().first()
    if not build or not build.pdf_path or not Path(build.pdf_path).exists():
        raise HTTPException(404, "PDF не найден")
    return FileResponse(build.pdf_path, media_type="application/pdf", filename="avgst-catalog.pdf")


@router.get("/builds/{build_id}/pages")
async def list_build_pages(
    build_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_user),
) -> dict:
    build = await _build_for_user(db, build_id, user)
    if not build.preview_dir:
        raise HTTPException(404, "Превью не найдены")
    return {"build_id": str(build.id), "page_count": build.page_count, "pages": _preview_urls(build)}


@router.get("/catalogs/{catalog_id}/preview")
async def list_catalog_pages(
    catalog_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_user),
) -> dict:
    await _catalog_for_user(db, catalog_id, user)
    result = await db.execute(
        select(Build).where(Build.catalog_id == catalog_id).order_by(Build.created_at.desc())
    )
    build = result.scalars().first()
    if not build or not build.preview_dir:
        raise HTTPException(404, "Превью не найдены")
    return {"build_id": str(build.id), "page_count": build.page_count, "pages": _preview_urls(build)}
