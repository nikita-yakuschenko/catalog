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

from app.core.access import can_access_proposal, can_delete_proposal
from app.core.auth import require_user
from app.core.config import settings
from app.core.db import SessionLocal, get_db
from app.domain.models import BuildStatus, CommercialProposal, ProposalBuild, ProposalSource
from app.domain.schemas import (
    ProposalBitrixIn,
    ProposalBuildOut,
    ProposalCreate,
    ProposalListItem,
    ProposalOut,
)
from app.services.bitrix_enrich import enrich_bitrix_event, extract_entity_ref, set_item_stage
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


async def _proposal_for_user(db: AsyncSession, proposal_id: UUID, user: dict) -> CommercialProposal:
    result = await db.execute(select(CommercialProposal).where(CommercialProposal.id == proposal_id))
    proposal = result.scalar_one_or_none()
    if not proposal or not can_access_proposal(proposal, user):
        raise HTTPException(404, "КП не найдено")
    return proposal


def _proposal_list_item(
    proposal: CommercialProposal,
    build: ProposalBuild | None,
    *,
    user: dict | None = None,
) -> ProposalListItem:
    doc = proposal.document if isinstance(proposal.document, dict) else {}
    client = doc.get("client") if isinstance(doc.get("client"), dict) else {}
    manager = doc.get("manager") if isinstance(doc.get("manager"), dict) else {}
    totals = doc.get("totals") if isinstance(doc.get("totals"), dict) else {}
    pdf_path = (build.pdf_path if build else "") or ""
    has_pdf = bool(pdf_path) and Path(pdf_path).exists() and (build.status == BuildStatus.ready if build else False)
    return ProposalListItem(
        id=proposal.id,
        external_id=proposal.external_id or "",
        source=proposal.source,
        status=proposal.status,
        project_name=str(doc.get("project_name") or ""),
        client_name=str(client.get("name") or client.get("company") or ""),
        manager_name=str(manager.get("name") or ""),
        grand_total=totals.get("grand") if totals.get("grand") is not None else doc.get("house_price"),
        created_at=proposal.created_at,
        updated_at=proposal.updated_at,
        build_status=build.status.value if build else None,
        has_pdf=has_pdf,
        can_delete=can_delete_proposal(proposal, user) if user else False,
    )


@router.get("/proposals", response_model=list[ProposalListItem], dependencies=[Depends(require_user)])
async def list_proposals(
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_user),
) -> list[ProposalListItem]:
    result = await db.execute(select(CommercialProposal).order_by(CommercialProposal.created_at.desc()))
    proposals = [p for p in result.scalars().all() if can_access_proposal(p, user)]
    if not proposals:
        return []

    ids = [p.id for p in proposals]
    builds_result = await db.execute(
        select(ProposalBuild)
        .where(ProposalBuild.proposal_id.in_(ids))
        .order_by(ProposalBuild.created_at.desc())
    )
    latest_by_proposal: dict[Any, ProposalBuild] = {}
    for build in builds_result.scalars().all():
        latest_by_proposal.setdefault(build.proposal_id, build)

    return [_proposal_list_item(p, latest_by_proposal.get(p.id), user=user) for p in proposals]


@router.post("/proposals", response_model=ProposalOut, dependencies=[Depends(require_user)])
async def create_proposal_api(
    payload: ProposalCreate, db: AsyncSession = Depends(get_db)
) -> CommercialProposal:
    return await create_proposal(db, payload, source=ProposalSource.api)


@router.post("/proposals/bitrix")
async def create_proposal_bitrix(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    _: None = Depends(_verify_bitrix_secret),
):
    raw_data = await _read_bitrix_payload(request)
    entity_type_id, item_id = extract_entity_ref(raw_data)
    expected = int(settings.bitrix_kp_entity_type_id or 0)
    if expected and entity_type_id != expected:
        logger.info(
            "bitrix webhook ignored: entityTypeId=%s item_id=%s (want KP=%s)",
            entity_type_id,
            item_id,
            expected,
        )
        # 200 so Bitrix does not retry; no DB / MarkItDown / build
        return {
            "status": "ignored",
            "reason": "unsupported_smart_process",
            "entity_type_id": entity_type_id,
            "item_id": item_id,
            "expected_entity_type_id": expected,
        }

    # Сразу «Подготовка КП», пока идёт парсинг/сборка
    prep_stage = settings.bitrix_prep_stage_id.strip()
    if prep_stage and entity_type_id and item_id:
        try:
            await set_item_stage(
                entity_type_id=int(entity_type_id),
                item_id=int(item_id),
                stage_id=prep_stage,
            )
        except Exception as exc:
            logger.warning("bitrix prep stage failed entity=%s id=%s: %s", entity_type_id, item_id, exc)

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


@router.post("/proposals/from-pdf", response_model=ProposalOut, dependencies=[Depends(require_user)])
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


@router.get("/proposals/{proposal_id}", response_model=ProposalOut, dependencies=[Depends(require_user)])
async def get_proposal(
    proposal_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_user),
) -> CommercialProposal:
    return await _proposal_for_user(db, proposal_id, user)


@router.post("/proposals/{proposal_id}/build", response_model=ProposalBuildOut, dependencies=[Depends(require_user)])
async def build_proposal(
    proposal_id: UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_user),
) -> ProposalBuild:
    proposal = await _proposal_for_user(db, proposal_id, user)
    build = ProposalBuild(proposal_id=proposal.id, status=BuildStatus.pending, stage="queued")
    db.add(build)
    await db.commit()
    await db.refresh(build)
    background_tasks.add_task(_background_proposal_build, build.id)
    return build


@router.get("/proposals/{proposal_id}/status", dependencies=[Depends(require_user)])
async def proposal_status(
    proposal_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_user),
) -> dict:
    proposal = await _proposal_for_user(db, proposal_id, user)
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


@router.get("/proposals/{proposal_id}/download", dependencies=[Depends(require_user)])
async def download_proposal(
    proposal_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_user),
) -> FileResponse:
    await _proposal_for_user(db, proposal_id, user)
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


def _unlink_quiet(path_str: str) -> None:
    if not path_str:
        return
    try:
        Path(path_str).unlink(missing_ok=True)
    except OSError:
        logger.warning("failed to delete file %s", path_str)


@router.delete("/proposals/{proposal_id}", dependencies=[Depends(require_user)])
async def delete_proposal(
    proposal_id: UUID,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(require_user),
) -> dict:
    proposal = await _proposal_for_user(db, proposal_id, user)
    if not can_delete_proposal(proposal, user):
        raise HTTPException(403, "Недостаточно прав для удаления КП")
    builds_result = await db.execute(
        select(ProposalBuild).where(ProposalBuild.proposal_id == proposal_id)
    )
    file_paths = [proposal.source_pdf_path]
    for build in builds_result.scalars().all():
        file_paths.append(build.pdf_path)
        file_paths.append(build.html_path)
    await db.delete(proposal)
    await db.commit()
    for path in file_paths:
        _unlink_quiet(path)
    return {"ok": True}
