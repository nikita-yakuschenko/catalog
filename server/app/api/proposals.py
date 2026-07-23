import json
import logging
from pathlib import Path
from typing import Any
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, Header, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.db import SessionLocal, get_db
from app.domain.models import BuildStatus, CommercialProposal, ProposalBuild, ProposalSource
from app.domain.schemas import ProposalBitrixIn, ProposalBuildOut, ProposalCreate, ProposalOut
from app.services.bitrix_enrich import enrich_bitrix_event
from app.services.proposal_build import run_proposal_build
from app.services.proposal_service import create_proposal

router = APIRouter()
logger = logging.getLogger(__name__)


def _verify_bitrix_secret(x_bitrix_webhook_secret: str | None = Header(default=None)) -> None:
    secret = settings.bitrix_webhook_secret.strip()
    if not secret:
        return
    if x_bitrix_webhook_secret != secret:
        raise HTTPException(401, "Неверный секрет вебхука Bitrix")


def _expand_form_keys(flat: dict[str, Any]) -> dict[str, Any]:
    """Expand data[FIELDS][ID]=… keys into nested dicts."""
    nested: dict[str, Any] = {}
    for key, value in flat.items():
        if "[" not in key:
            nested[key] = value
            continue
        parts = key.replace("]", "").split("[")
        cur: Any = nested
        for part in parts[:-1]:
            if not isinstance(cur, dict):
                break
            cur = cur.setdefault(part, {})
        else:
            if isinstance(cur, dict):
                cur[parts[-1]] = value
    return nested or flat


async def _read_bitrix_payload(request: Request) -> dict[str, Any]:
    from urllib.parse import parse_qs

    content_type = (request.headers.get("content-type") or "").lower()
    raw = await request.body()
    preview = raw[:4000].decode("utf-8", errors="replace")
    logger.info("bitrix webhook content-type=%s bytes=%s body=%s", content_type, len(raw), preview)

    if not raw.strip():
        return {}

    if "application/json" in content_type or raw.lstrip()[:1] in (b"{", b"["):
        try:
            parsed = json.loads(raw)
            return parsed if isinstance(parsed, dict) else {"_list": parsed}
        except json.JSONDecodeError as exc:
            logger.warning("bitrix webhook invalid json: %s", exc)
            raise HTTPException(422, f"Invalid JSON: {exc}") from exc

    pairs = parse_qs(raw.decode("utf-8", errors="replace"), keep_blank_values=True)
    flat = {k: (v[0] if len(v) == 1 else v) for k, v in pairs.items()}
    return _expand_form_keys(flat)


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
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(_verify_bitrix_secret),
) -> CommercialProposal:
    raw_data = await _read_bitrix_payload(request)
    enrichment = await enrich_bitrix_event(raw_data)
    try:
        payload = ProposalBitrixIn.model_validate(enrichment.payload)
    except ValidationError as exc:
        logger.warning("bitrix webhook validation failed: %s", exc.errors())
        raise HTTPException(422, {"detail": exc.errors(), "received": enrichment.payload}) from exc

    external_id = payload.deal_id or payload.lead_id or ""
    body = payload.model_dump()
    if enrichment.warnings:
        body.setdefault("meta", {}).setdefault("bitrix", {})["warnings"] = enrichment.warnings

    logger.info(
        "bitrix webhook accepted deal_id=%s project_name=%s file=%s warnings=%s",
        external_id,
        payload.project_name,
        enrichment.pdf_filename if enrichment.pdf_bytes else None,
        enrichment.warnings,
    )
    proposal = await create_proposal(
        db,
        payload,
        source=ProposalSource.bitrix,
        external_id=str(external_id),
        request_payload=body,
        pdf_bytes=enrichment.pdf_bytes,
        pdf_filename=enrichment.pdf_filename,
    )

    # Kick off KP PDF build when we have enough to render (or even without — assembler handles empty).
    build = ProposalBuild(proposal_id=proposal.id, status=BuildStatus.pending, stage="queued")
    db.add(build)
    await db.commit()
    await db.refresh(build)
    background_tasks.add_task(_background_proposal_build, build.id)
    return proposal


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
