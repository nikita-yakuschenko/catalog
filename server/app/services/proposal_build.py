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
        if proposal.project and proposal.project.assets:
            primary = next((a for a in proposal.project.assets if a.is_primary and not a.excluded), None)
            asset = primary or next((a for a in proposal.project.assets if not a.excluded), None)
            if asset and asset.local_path:
                project_image = _asset_file_url(asset.local_path, role="hero")

        html = ProposalAssembler().assemble(proposal.document, project_image_url=project_image)
        html_path = out_dir / "proposal.html"
        html_path.write_text(html, encoding="utf-8")
        build.html_path = str(html_path)

        build.stage = "render"
        build.log = list(build.log) + [{"stage": "render", "at": _now()}]
        await session.commit()

        renderer, _ = get_renderer("screen")
        pdf_path = out_dir / "proposal.pdf"
        await renderer.render_html(html, pdf_path, landscape=False)

        build.pdf_path = str(pdf_path)
        build.status = BuildStatus.ready
        build.stage = "done"
        proposal.status = ProposalStatus.ready
        build.finished_at = datetime.now(timezone.utc)
        build.log = list(build.log) + [{"stage": "done", "at": _now()}]
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
