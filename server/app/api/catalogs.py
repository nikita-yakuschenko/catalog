from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.db import SessionLocal, get_db
from app.domain.models import (
    Build,
    BuildStatus,
    Catalog,
    CatalogProject,
    CatalogStatus,
    HouseProject,
    OutputProfile,
)
from app.domain.schemas import (
    BuildOut,
    CatalogCreate,
    CatalogOut,
    CatalogProjectUpdate,
    CatalogUpdate,
    ReorderItem,
)
from app.services.build import run_build
from app.services.preflight import PreflightService

router = APIRouter()


def _catalog_query():
    return select(Catalog).options(
        selectinload(Catalog.projects).selectinload(CatalogProject.project).selectinload(HouseProject.assets)
    )


@router.get("/catalogs", response_model=list[CatalogOut])
async def list_catalogs(db: AsyncSession = Depends(get_db)) -> list[Catalog]:
    result = await db.execute(_catalog_query().order_by(Catalog.created_at.desc()))
    return list(result.scalars().all())


@router.post("/catalogs", response_model=CatalogOut)
async def create_catalog(payload: CatalogCreate, db: AsyncSession = Depends(get_db)) -> Catalog:
    catalog = Catalog(
        name=payload.name,
        title=payload.title,
        subtitle=payload.subtitle,
        year=payload.year,
        format=payload.format,
        output_profile=payload.output_profile,
        show_prices=payload.show_prices,
        show_project_links=payload.show_project_links,
        price_actual_at=payload.price_actual_at,
        show_contents=payload.show_contents,
        show_introduction=payload.show_introduction,
        show_dividers=payload.show_dividers,
        show_contacts=payload.show_contacts,
        cover_variant=payload.cover_variant,
        theme=payload.theme,
        layout_strategy=payload.layout_strategy,
        contacts=payload.contacts,
        settings=payload.settings,
    )
    db.add(catalog)
    await db.flush()
    for idx, pid in enumerate(payload.project_ids):
        db.add(CatalogProject(catalog_id=catalog.id, project_id=pid, order=idx))
    await db.commit()
    result = await db.execute(_catalog_query().where(Catalog.id == catalog.id))
    return result.scalar_one()


@router.get("/catalogs/{catalog_id}", response_model=CatalogOut)
async def get_catalog(catalog_id: UUID, db: AsyncSession = Depends(get_db)) -> Catalog:
    result = await db.execute(_catalog_query().where(Catalog.id == catalog_id))
    catalog = result.scalar_one_or_none()
    if not catalog:
        raise HTTPException(404, "Каталог не найден")
    return catalog


@router.patch("/catalogs/{catalog_id}", response_model=CatalogOut)
async def update_catalog(
    catalog_id: UUID, payload: CatalogUpdate, db: AsyncSession = Depends(get_db)
) -> Catalog:
    result = await db.execute(_catalog_query().where(Catalog.id == catalog_id))
    catalog = result.scalar_one_or_none()
    if not catalog:
        raise HTTPException(404, "Каталог не найден")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(catalog, key, value)
    await db.commit()
    result = await db.execute(_catalog_query().where(Catalog.id == catalog_id))
    return result.scalar_one()


@router.delete("/catalogs/{catalog_id}")
async def delete_catalog(catalog_id: UUID, db: AsyncSession = Depends(get_db)) -> dict:
    result = await db.execute(select(Catalog).where(Catalog.id == catalog_id))
    catalog = result.scalar_one_or_none()
    if not catalog:
        raise HTTPException(404, "Каталог не найден")
    await db.delete(catalog)
    await db.commit()
    return {"ok": True}


@router.post("/catalogs/{catalog_id}/duplicate", response_model=CatalogOut)
async def duplicate_catalog(catalog_id: UUID, db: AsyncSession = Depends(get_db)) -> Catalog:
    result = await db.execute(_catalog_query().where(Catalog.id == catalog_id))
    src = result.scalar_one_or_none()
    if not src:
        raise HTTPException(404, "Каталог не найден")
    clone = Catalog(
        name=f"{src.name} (копия)",
        status=CatalogStatus.draft,
        format=src.format,
        output_profile=src.output_profile,
        title=src.title,
        subtitle=src.subtitle,
        year=src.year,
        show_prices=src.show_prices,
        show_project_links=src.show_project_links,
        price_actual_at=src.price_actual_at,
        show_contents=src.show_contents,
        show_introduction=src.show_introduction,
        show_dividers=src.show_dividers,
        show_contacts=src.show_contacts,
        cover_variant=src.cover_variant,
        theme=src.theme,
        layout_strategy=src.layout_strategy,
        contacts=src.contacts,
        settings=src.settings,
    )
    db.add(clone)
    await db.flush()
    for cp in src.projects:
        db.add(
            CatalogProject(
                catalog_id=clone.id,
                project_id=cp.project_id,
                order=cp.order,
                layout_variant_override=cp.layout_variant_override,
                custom_title=cp.custom_title,
            )
        )
    await db.commit()
    result = await db.execute(_catalog_query().where(Catalog.id == clone.id))
    return result.scalar_one()


@router.post("/catalogs/{catalog_id}/projects")
async def add_projects(
    catalog_id: UUID, project_ids: list[UUID], db: AsyncSession = Depends(get_db)
) -> CatalogOut:
    result = await db.execute(_catalog_query().where(Catalog.id == catalog_id))
    catalog = result.scalar_one_or_none()
    if not catalog:
        raise HTTPException(404, "Каталог не найден")
    existing = {cp.project_id for cp in catalog.projects}
    order = max([cp.order for cp in catalog.projects], default=-1) + 1
    for pid in project_ids:
        if pid in existing:
            continue
        db.add(CatalogProject(catalog_id=catalog.id, project_id=pid, order=order))
        order += 1
    await db.commit()
    result = await db.execute(_catalog_query().where(Catalog.id == catalog_id))
    return result.scalar_one()


@router.patch("/catalogs/{catalog_id}/projects/reorder")
async def reorder_projects(
    catalog_id: UUID, items: list[ReorderItem], db: AsyncSession = Depends(get_db)
) -> CatalogOut:
    result = await db.execute(_catalog_query().where(Catalog.id == catalog_id))
    catalog = result.scalar_one_or_none()
    if not catalog:
        raise HTTPException(404, "Каталог не найден")
    by_pid = {cp.project_id: cp for cp in catalog.projects}
    for item in items:
        if item.project_id in by_pid:
            by_pid[item.project_id].order = item.order
    await db.commit()
    result = await db.execute(_catalog_query().where(Catalog.id == catalog_id))
    return result.scalar_one()


@router.patch("/catalogs/{catalog_id}/projects/{project_id}")
async def update_catalog_project(
    catalog_id: UUID,
    project_id: UUID,
    payload: CatalogProjectUpdate,
    db: AsyncSession = Depends(get_db),
) -> CatalogOut:
    result = await db.execute(
        select(CatalogProject).where(
            CatalogProject.catalog_id == catalog_id, CatalogProject.project_id == project_id
        )
    )
    cp = result.scalar_one_or_none()
    if not cp:
        raise HTTPException(404, "Проект каталога не найден")
    data = payload.model_dump(exclude_unset=True)
    if "selected_asset_ids" in data and data["selected_asset_ids"] is not None:
        data["selected_asset_ids"] = [str(x) for x in data["selected_asset_ids"]]
    for key, value in data.items():
        setattr(cp, key, value)
    await db.commit()
    result = await db.execute(_catalog_query().where(Catalog.id == catalog_id))
    return result.scalar_one()


@router.delete("/catalogs/{catalog_id}/projects/{project_id}")
async def remove_catalog_project(
    catalog_id: UUID, project_id: UUID, db: AsyncSession = Depends(get_db)
) -> dict:
    result = await db.execute(
        select(CatalogProject).where(
            CatalogProject.catalog_id == catalog_id, CatalogProject.project_id == project_id
        )
    )
    cp = result.scalar_one_or_none()
    if not cp:
        raise HTTPException(404, "Проект каталога не найден")
    await db.delete(cp)
    await db.commit()
    return {"ok": True}


@router.post("/catalogs/{catalog_id}/preflight")
async def preflight_catalog(catalog_id: UUID, db: AsyncSession = Depends(get_db)) -> dict:
    result = await db.execute(_catalog_query().where(Catalog.id == catalog_id))
    catalog = result.scalar_one_or_none()
    if not catalog:
        raise HTTPException(404, "Каталог не найден")
    projects = [cp.project for cp in catalog.projects if cp.project]
    return PreflightService().run(catalog, projects).to_dict()


async def _background_build(build_id: UUID) -> None:
    async with SessionLocal() as session:
        await run_build(session, build_id)


@router.post("/catalogs/{catalog_id}/render", response_model=BuildOut)
@router.post("/catalogs/{catalog_id}/build", response_model=BuildOut)
async def build_catalog(
    catalog_id: UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> Build:
    result = await db.execute(select(Catalog).where(Catalog.id == catalog_id))
    catalog = result.scalar_one_or_none()
    if not catalog:
        raise HTTPException(404, "Каталог не найден")
    build = Build(
        catalog_id=catalog.id,
        status=BuildStatus.pending,
        output_profile=catalog.output_profile,
        stage="queued",
    )
    db.add(build)
    await db.commit()
    await db.refresh(build)
    background_tasks.add_task(_background_build, build.id)
    return build


@router.get("/catalogs/{catalog_id}/status")
async def catalog_status(catalog_id: UUID, db: AsyncSession = Depends(get_db)) -> dict:
    result = await db.execute(
        select(Build).where(Build.catalog_id == catalog_id).order_by(Build.created_at.desc())
    )
    build = result.scalars().first()
    cat = await db.execute(select(Catalog).where(Catalog.id == catalog_id))
    catalog = cat.scalar_one_or_none()
    if not catalog:
        raise HTTPException(404, "Каталог не найден")
    return {
        "catalog_status": catalog.status,
        "build": BuildOut.model_validate(build) if build else None,
    }


@router.get("/catalogs/{catalog_id}/preflight-report")
async def catalog_preflight_report(catalog_id: UUID, db: AsyncSession = Depends(get_db)) -> dict:
    result = await db.execute(
        select(Build).where(Build.catalog_id == catalog_id).order_by(Build.created_at.desc())
    )
    build = result.scalars().first()
    if not build or not build.preflight_report:
        raise HTTPException(404, "Отчёт не найден")
    return build.preflight_report
