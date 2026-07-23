"""Build commercial proposal PDF."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.domain.models import (
    BuildStatus,
    CommercialProposal,
    HouseProject,
    ProposalBuild,
    ProposalStatus,
)
from app.renderers import get_renderer
from app.services.assembler import _asset_file_url
from app.services.proposal_assembler import ProposalAssembler


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


async def run_proposal_build(session: AsyncSession, build_id: UUID) -> ProposalBuild:
    result = await session.execute(select(ProposalBuild).where(ProposalBuild.id == build_id))
    build = result.scalar_one()
    prop_result = await session.execute(
        select(CommercialProposal)
        .where(CommercialProposal.id == build.proposal_id)
        .options(selectinload(CommercialProposal.project).selectinload(HouseProject.assets))
    )
    proposal = prop_result.scalar_one()

    build.status = BuildStatus.running
    build.stage = "assemble"
    proposal.status = ProposalStatus.building
    build.log = list(build.log or []) + [{"stage": "assemble", "at": _now()}]
    await session.commit()

    out_dir = Path(settings.output_dir) / "proposals" / str(proposal.id) / str(build.id)
    out_dir.mkdir(parents=True, exist_ok=True)

    try:
        project_image = ""
        project = proposal.project
        if project and project.assets:
            primary = next((a for a in project.assets if a.is_primary and not a.excluded), None)
            asset = primary or next((a for a in project.assets if not a.excluded), None)
            if asset and asset.local_path:
                project_image = _asset_file_url(asset.local_path, role="hero")

        html = ProposalAssembler().assemble(
            proposal.document,
            project=project,
            project_image_url=project_image,
        )
        html_path = out_dir / "proposal.html"
        html_path.write_text(html, encoding="utf-8")
        build.html_path = str(html_path)

        build.stage = "render"
        build.log = list(build.log) + [{"stage": "render", "at": _now()}]
        await session.commit()

        renderer, _ = get_renderer("screen")
        pdf_path = out_dir / "proposal.pdf"
        await renderer.render_html(html, pdf_path, landscape=True)

        build.pdf_path = str(pdf_path)
        build.status = BuildStatus.ready
        build.stage = "done"
        proposal.status = ProposalStatus.ready
        build.finished_at = datetime.now(timezone.utc)
        build.log = list(build.log) + [{"stage": "done", "at": _now()}]

        # Push finished KP back to Bitrix Disk when webhook/folder configured.
        try:
            from app.services.bitrix_enrich import upload_proposal_pdf

            req = proposal.request_payload if isinstance(proposal.request_payload, dict) else {}
            bitrix_meta = ((req.get("meta") or {}).get("bitrix") or {}) if isinstance(req, dict) else {}
            doc = proposal.document if isinstance(proposal.document, dict) else {}
            totals = doc.get("totals") if isinstance(doc.get("totals"), dict) else {}
            opportunity = totals.get("grand")
            if opportunity is None:
                opportunity = doc.get("house_price")
            assigned = bitrix_meta.get("assigned_by_id")
            if assigned is None and isinstance(req.get("raw"), dict):
                item_raw = (req.get("raw") or {}).get("item") or {}
                assigned = item_raw.get("assignedById") or item_raw.get("ASSIGNED_BY_ID")
            upload_info = await upload_proposal_pdf(
                pdf_path=pdf_path,
                entity_type_id=bitrix_meta.get("entity_type_id"),
                item_id=bitrix_meta.get("item_id"),
                parent_folder_id=bitrix_meta.get("source_parent_folder_id"),
                opportunity=int(opportunity) if opportunity is not None else None,
                project_name=str(doc.get("project_name") or ""),
                assigned_by_id=int(assigned) if assigned not in (None, "") else None,
            )
            build.log = list(build.log) + [{"stage": "bitrix_upload", "at": _now(), "info": upload_info}]
        except Exception as upload_exc:
            build.log = list(build.log) + [
                {"stage": "bitrix_upload", "at": _now(), "error": str(upload_exc)}
            ]

        await session.commit()
        return build
    except Exception as exc:
        build.status = BuildStatus.failed
        build.stage = "failed"
        build.error_message = str(exc)
        proposal.status = ProposalStatus.failed
        build.finished_at = datetime.now(timezone.utc)
        build.log = list(build.log) + [{"stage": "failed", "at": _now(), "error": str(exc)}]
        await session.commit()
        raise
