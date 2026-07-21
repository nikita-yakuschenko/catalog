from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, Header, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db import SessionLocal, get_db
from app.domain.models import BuildStatus, CommercialProposal, ProposalBuild, ProposalSource
from app.domain.schemas import ProposalBitrixIn, ProposalBuildOut, ProposalCreate, ProposalOut
from app.services.proposal_build import run_proposal_build
from app.services.proposal_service import create_proposal

router = APIRouter()


def _verify_bitrix_secret(x_bitrix_webhook_secret: str | None = Header(default=None)) -> None:
    secret = settings.bitrix_webhook_secret.strip()
    if not secret:
        return
    if x_bitrix_webhook_secret != secret:
        raise HTTPException(401, "Неверный секрет вебхука Bitrix")


async def _background_proposal_build(build_id: UUID) -> None:
    async with SessionLocal() as session:
        await run_proposal_build(session, build_id)


@router.get("/proposals", response_model=list[ProposalOut])
async def list_proposals(db: AsyncSession = Depends(get_db)) -> list[CommercialProposal]:
    result = await db.execute(select(CommercialProposal).order_by(CommercialProposal.created_at.desc()))
    return list(result.scalars().all())


@router.post("/proposals", response_model=ProposalOut)
async def create_proposal_api(
    payload: ProposalCreate, db: AsyncSession = Depends(get_db)
) -> CommercialProposal:
    return await create_proposal(db, payload, source=ProposalSource.api)


@router.post("/proposals/bitrix", response_model=ProposalOut)
async def create_proposal_bitrix(
    payload: ProposalBitrixIn,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(_verify_bitrix_secret),
) -> CommercialProposal:
    external_id = payload.deal_id or payload.lead_id or ""
    body = payload.model_dump()
    return await create_proposal(
        db,
        payload,
        source=ProposalSource.bitrix,
        external_id=str(external_id),
        request_payload=body,
    )


@router.post("/proposals/from-pdf", response_model=ProposalOut)
async def create_proposal_from_pdf(
    file: UploadFile = File(...),
    payload_json: str = Form(default="{}"),
    db: AsyncSession = Depends(get_db),
) -> CommercialProposal:
    import json

    try:
        raw = json.loads(payload_json) if payload_json.strip() else {}
    except json.JSONDecodeError as exc:
        raise HTTPException(400, f"payload_json: {exc}") from exc
    payload = ProposalCreate.model_validate(raw)
    content = await file.read()
    if not content:
        raise HTTPException(400, "Пустой PDF")
    return await create_proposal(
        db,
        payload,
        source=ProposalSource.pdf,
        pdf_bytes=content,
        pdf_filename=file.filename or "source.pdf",
    )


@router.get("/proposals/{proposal_id}", response_model=ProposalOut)
async def get_proposal(proposal_id: UUID, db: AsyncSession = Depends(get_db)) -> CommercialProposal:
    result = await db.execute(select(CommercialProposal).where(CommercialProposal.id == proposal_id))
    proposal = result.scalar_one_or_none()
    if not proposal:
        raise HTTPException(404, "КП не найдено")
    return proposal


@router.post("/proposals/{proposal_id}/build", response_model=ProposalBuildOut)
async def build_proposal(
    proposal_id: UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> ProposalBuild:
    result = await db.execute(select(CommercialProposal).where(CommercialProposal.id == proposal_id))
    proposal = result.scalar_one_or_none()
    if not proposal:
        raise HTTPException(404, "КП не найдено")
    build = ProposalBuild(proposal_id=proposal.id, status=BuildStatus.pending, stage="queued")
    db.add(build)
    await db.commit()
    await db.refresh(build)
    background_tasks.add_task(_background_proposal_build, build.id)
    return build


@router.get("/proposals/{proposal_id}/status")
async def proposal_status(proposal_id: UUID, db: AsyncSession = Depends(get_db)) -> dict:
    prop = await db.execute(select(CommercialProposal).where(CommercialProposal.id == proposal_id))
    proposal = prop.scalar_one_or_none()
    if not proposal:
        raise HTTPException(404, "КП не найдено")
    build_result = await db.execute(
        select(ProposalBuild)
        .where(ProposalBuild.proposal_id == proposal_id)
        .order_by(ProposalBuild.created_at.desc())
    )
    build = build_result.scalars().first()
    return {
        "proposal_status": proposal.status.value,
        "build": ProposalBuildOut.model_validate(build) if build else None,
    }


@router.get("/proposals/{proposal_id}/download")
async def download_proposal(proposal_id: UUID, db: AsyncSession = Depends(get_db)) -> FileResponse:
    build_result = await db.execute(
        select(ProposalBuild)
        .where(ProposalBuild.proposal_id == proposal_id, ProposalBuild.status == BuildStatus.ready)
        .order_by(ProposalBuild.created_at.desc())
    )
    build = build_result.scalars().first()
    if not build or not build.pdf_path:
        raise HTTPException(404, "PDF ещё не готов")
    path = Path(build.pdf_path)
    if not path.exists():
        raise HTTPException(404, "Файл не найден")
    return FileResponse(path, media_type="application/pdf", filename=f"proposal-{proposal_id}.pdf")
