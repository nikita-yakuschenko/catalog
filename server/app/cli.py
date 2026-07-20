import asyncio
from datetime import date
from pathlib import Path
from typing import Optional
from uuid import UUID

import typer
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.db import SessionLocal
from app.domain.models import Build, BuildStatus, Catalog, CatalogProject, HouseProject, Technology
from app.services.build import run_build
from app.services.preflight import PreflightService
from app.services.sync import sync_projects

cli = typer.Typer(help="AVGST Catalog Builder CLI")


def _run(coro):
    return asyncio.run(coro)


@cli.command("sync-projects")
def sync_projects_cmd(download_assets: bool = True) -> None:
    async def _inner():
        async with SessionLocal() as session:
            result = await sync_projects(session, download_assets=download_assets)
            typer.echo(result.model_dump_json(indent=2))

    _run(_inner())


@cli.command("validate-projects")
def validate_projects_cmd() -> None:
    async def _inner():
        async with SessionLocal() as session:
            result = await session.execute(
                select(HouseProject).options(selectinload(HouseProject.assets))
            )
            projects = list(result.scalars().all())
            catalog = Catalog(name="validate", show_prices=True, price_actual_at=date.today())
            report = PreflightService().run(catalog, projects)
            typer.echo(report.to_dict())

    _run(_inner())


@cli.command("create-catalog")
def create_catalog_cmd(
    name: str = "AVGST — 20 проектов",
    modular_limit: int = 10,
    panel_limit: int = 10,
) -> None:
    async def _inner():
        async with SessionLocal() as session:
            modular = (
                await session.execute(
                    select(HouseProject)
                    .where(HouseProject.technology == Technology.modular, HouseProject.active.is_(True))
                    .order_by(HouseProject.sort_order, HouseProject.short_name)
                    .limit(modular_limit)
                )
            ).scalars().all()
            panel = (
                await session.execute(
                    select(HouseProject)
                    .where(HouseProject.technology == Technology.panel, HouseProject.active.is_(True))
                    .order_by(HouseProject.sort_order, HouseProject.short_name)
                    .limit(panel_limit)
                )
            ).scalars().all()
            catalog = Catalog(
                name=name,
                title=f"{len(modular) + len(panel)} проектов домов",
                subtitle="Модульные и панельно-каркасные дома",
                price_actual_at=date.today(),
            )
            session.add(catalog)
            await session.flush()
            order = 0
            for p in list(modular) + list(panel):
                session.add(CatalogProject(catalog_id=catalog.id, project_id=p.id, order=order))
                order += 1
            await session.commit()
            typer.echo(str(catalog.id))

    _run(_inner())


@cli.command("preflight")
def preflight_cmd(catalog_id: UUID) -> None:
    async def _inner():
        async with SessionLocal() as session:
            result = await session.execute(
                select(Catalog)
                .where(Catalog.id == catalog_id)
                .options(
                    selectinload(Catalog.projects)
                    .selectinload(CatalogProject.project)
                    .selectinload(HouseProject.assets)
                )
            )
            catalog = result.scalar_one()
            projects = [cp.project for cp in catalog.projects if cp.project]
            report = PreflightService().run(catalog, projects)
            typer.echo(report.to_dict())

    _run(_inner())


@cli.command("render")
def render_cmd(catalog_id: UUID, profile: str = "screen") -> None:
    async def _inner():
        async with SessionLocal() as session:
            catalog = (
                await session.execute(select(Catalog).where(Catalog.id == catalog_id))
            ).scalar_one()
            from app.domain.models import OutputProfile

            build = Build(
                catalog_id=catalog.id,
                status=BuildStatus.pending,
                output_profile=OutputProfile(profile),
            )
            session.add(build)
            await session.commit()
            await session.refresh(build)
            build = await run_build(session, build.id)
            typer.echo(f"status={build.status} pdf={build.pdf_path} pages={build.page_count}")

    _run(_inner())


if __name__ == "__main__":
    cli()
