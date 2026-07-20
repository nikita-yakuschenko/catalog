"""Catalog build orchestration: preflight -> assemble -> PDF -> previews."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

import fitz  # PyMuPDF
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.domain.models import Build, BuildStatus, Catalog, CatalogStatus, HouseProject, OutputProfile
from app.renderers import get_renderer
from app.services.assembler import CatalogAssembler
from app.services.pdf_optimize import optimize_pdf_images
from app.services.preflight import PreflightService


async def run_build(session: AsyncSession, build_id: UUID) -> Build:
    result = await session.execute(select(Build).where(Build.id == build_id))
    build = result.scalar_one()
    catalog_result = await session.execute(
        select(Catalog)
        .where(Catalog.id == build.catalog_id)
        .options(selectinload(Catalog.projects))
    )
    catalog = catalog_result.scalar_one()

    # Load projects with assets
    project_ids = [cp.project_id for cp in catalog.projects]
    projects_result = await session.execute(
        select(HouseProject)
        .where(HouseProject.id.in_(project_ids))
        .options(selectinload(HouseProject.assets))
    )
    projects = list(projects_result.scalars().all())
    by_id = {p.id: p for p in projects}

    build.status = BuildStatus.running
    catalog.status = CatalogStatus.rendering
    build.stage = "preflight"
    build.log = list(build.log or []) + [{"stage": "preflight", "at": _now()}]
    await session.commit()

    out_dir = Path(settings.output_dir) / str(catalog.id) / str(build.id)
    out_dir.mkdir(parents=True, exist_ok=True)

    try:
        ordered_projects = [by_id[cp.project_id] for cp in sorted(catalog.projects, key=lambda x: x.order) if cp.project_id in by_id]
        report = PreflightService().run(catalog, ordered_projects)
        report_path = out_dir / "preflight-report.json"
        report_path.write_text(json.dumps(report.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
        build.preflight_report = report.to_dict()

        if report.status == "failed" and build.output_profile == OutputProfile.print:
            raise RuntimeError("Preflight failed for print profile")

        build.stage = "assemble"
        build.log = list(build.log) + [{"stage": "assemble", "at": _now()}]
        await session.commit()

        assembled = CatalogAssembler().assemble(catalog, list(catalog.projects), by_id)
        html_path = out_dir / "catalog.html"
        html_path.write_text(assembled.html, encoding="utf-8")

        # Persist chosen layouts
        for cp in catalog.projects:
            lid = assembled.layout_map.get(str(cp.project_id))
            if lid:
                cp.layout_variant = lid

        build.stage = "render"
        build.log = list(build.log) + [{"stage": "render", "at": _now(), "warnings": assembled.warnings}]
        await session.commit()

        renderer, render_warnings = get_renderer(build.output_profile.value)
        if render_warnings:
            pref = dict(build.preflight_report or {})
            warns = list(pref.get("warnings") or [])
            for w in render_warnings:
                warns.append({"code": "renderer", "level": "warning", "message": w, "project_id": None})
            pref["warnings"] = warns
            if pref.get("status") == "passed":
                pref["status"] = "warning"
            build.preflight_report = pref

        pdf_path = out_dir / "catalog.pdf"
        await renderer.render_html(assembled.html, pdf_path)
        # Chromium embeds photos as FlateDecode (huge) — recompress to JPEG in-place.
        opt = optimize_pdf_images(pdf_path)
        build.pdf_path = str(pdf_path)
        build.log = list(build.log) + [
            {
                "stage": "pdf_optimize",
                "at": _now(),
                "before_mb": round(opt["before_bytes"] / 1e6, 2),
                "after_mb": round(opt["after_bytes"] / 1e6, 2),
                "replaced": opt["replaced"],
            }
        ]

        build.stage = "previews"
        build.log = list(build.log) + [{"stage": "previews", "at": _now()}]
        await session.commit()

        preview_dir = out_dir / "pages"
        page_count = _export_previews(pdf_path, preview_dir)
        build.preview_dir = str(preview_dir)
        build.page_count = page_count

        build.status = BuildStatus.ready
        build.stage = "done"
        catalog.status = CatalogStatus.ready
        build.finished_at = datetime.now(timezone.utc)
        build.log = list(build.log) + [{"stage": "done", "at": _now()}]
        await session.commit()
        return build
    except Exception as exc:
        build.status = BuildStatus.failed
        build.stage = "failed"
        build.error_message = str(exc)
        catalog.status = CatalogStatus.failed
        build.finished_at = datetime.now(timezone.utc)
        build.log = list(build.log) + [{"stage": "failed", "at": _now(), "error": str(exc)}]
        await session.commit()
        return build


def _export_previews(pdf_path: Path, preview_dir: Path) -> int:
    preview_dir.mkdir(parents=True, exist_ok=True)
    doc = fitz.open(pdf_path)
    for i, page in enumerate(doc, start=1):
        pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5))
        pix.save(str(preview_dir / f"page-{i:03d}.jpg"))
    count = doc.page_count
    doc.close()
    return count


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()
