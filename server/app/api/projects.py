from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.db import get_db
from app.domain.models import HouseProject, ProjectAsset, Technology
from app.domain.schemas import AssetOut, AssetUpdate, ProjectOut, ProjectUpdate

router = APIRouter()


@router.get("/projects", response_model=list[ProjectOut])
async def list_projects(
    technology: Optional[Technology] = None,
    q: Optional[str] = None,
    active: Optional[bool] = True,
    db: AsyncSession = Depends(get_db),
) -> list[HouseProject]:
    stmt = select(HouseProject).options(selectinload(HouseProject.assets)).order_by(
        HouseProject.technology, HouseProject.sort_order, HouseProject.short_name
    )
    if technology:
        stmt = stmt.where(HouseProject.technology == technology)
    if active is not None:
        stmt = stmt.where(HouseProject.active == active)
    result = await db.execute(stmt)
    projects = list(result.scalars().all())
    if q:
        ql = q.lower()
        projects = [p for p in projects if ql in p.name.lower() or ql in p.short_name.lower()]
    return projects


@router.get("/projects/{project_id}", response_model=ProjectOut)
async def get_project(project_id: UUID, db: AsyncSession = Depends(get_db)) -> HouseProject:
    result = await db.execute(
        select(HouseProject)
        .where(HouseProject.id == project_id)
        .options(selectinload(HouseProject.assets))
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(404, "Проект не найден")
    return project


@router.patch("/projects/{project_id}", response_model=ProjectOut)
async def update_project(
    project_id: UUID, payload: ProjectUpdate, db: AsyncSession = Depends(get_db)
) -> HouseProject:
    result = await db.execute(
        select(HouseProject)
        .where(HouseProject.id == project_id)
        .options(selectinload(HouseProject.assets))
    )
    project = result.scalar_one_or_none()
    if not project:
        raise HTTPException(404, "Проект не найден")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(project, key, value)
    await db.commit()
    await db.refresh(project)
    return project


@router.get("/projects/{project_id}/assets", response_model=list[AssetOut])
async def list_assets(project_id: UUID, db: AsyncSession = Depends(get_db)) -> list[ProjectAsset]:
    result = await db.execute(
        select(ProjectAsset)
        .where(ProjectAsset.project_id == project_id)
        .order_by(ProjectAsset.sort_order)
    )
    return list(result.scalars().all())


@router.patch("/assets/{asset_id}", response_model=AssetOut)
async def update_asset(
    asset_id: UUID, payload: AssetUpdate, db: AsyncSession = Depends(get_db)
) -> ProjectAsset:
    result = await db.execute(select(ProjectAsset).where(ProjectAsset.id == asset_id))
    asset = result.scalar_one_or_none()
    if not asset:
        raise HTTPException(404, "Ассет не найден")
    data = payload.model_dump(exclude_unset=True)
    if data.get("is_primary"):
        siblings = await db.execute(
            select(ProjectAsset).where(ProjectAsset.project_id == asset.project_id)
        )
        for s in siblings.scalars().all():
            s.is_primary = False
    for key, value in data.items():
        setattr(asset, key, value)
    await db.commit()
    await db.refresh(asset)
    return asset
