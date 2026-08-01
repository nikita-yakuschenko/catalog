"""Create and enrich commercial proposals."""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.domain.models import CommercialProposal, HouseProject, ProposalSource, ProposalStatus
from app.domain.schemas import ProposalCreate
from app.services.proposal_intake import ingest_estimate_file
from app.services.proposal_parse import merge_documents, normalize_document

logger = logging.getLogger(__name__)


async def match_project_id(session: AsyncSession, project_name: str) -> Optional[UUID]:
    if not project_name.strip():
        return None
    result = await session.execute(select(HouseProject))
    projects = list(result.scalars().all())
    needle = project_name.strip().lower()
    for project in projects:
        if project.short_name.lower() == needle or project.name.lower() == needle:
            return project.id
    for project in projects:
        if needle in project.short_name.lower() or needle in project.name.lower():
            return project.id
    return None


def cleanup_intake_storage() -> int:
    """Remove leftover Bitrix/PDF intake files — only markdown/document stay in DB."""
    intake = Path(settings.storage_dir) / "proposals" / "intake"
    if not intake.is_dir():
        return 0
    removed = 0
    for path in intake.iterdir():
        if not path.is_file():
            continue
        try:
            path.unlink()
            removed += 1
        except OSError as exc:
            logger.warning("failed to delete intake file %s: %s", path, exc)
    return removed


async def create_proposal(
    session: AsyncSession,
    payload: ProposalCreate,
    *,
    source: ProposalSource,
    external_id: str = "",
    request_payload: Optional[dict[str, Any]] = None,
    pdf_bytes: Optional[bytes] = None,
    pdf_filename: str = "source.pdf",
) -> CommercialProposal:
    structured = payload.model_dump()
    parsed_doc: dict[str, Any] = {}
    markdown = ""

    if pdf_bytes:
        # Temp file only for MarkItDown/table extract — do not keep Bitrix originals on disk.
        suffix = Path(pdf_filename).suffix or ".bin"
        tmp_path: Optional[Path] = None
        try:
            with tempfile.NamedTemporaryFile(prefix="kp_intake_", suffix=suffix, delete=False) as tmp:
                tmp.write(pdf_bytes)
                tmp_path = Path(tmp.name)
            parsed_doc, markdown, method = ingest_estimate_file(tmp_path)
            logger.info(
                "proposal intake file=%s method=%s house=%s options=%s",
                pdf_filename,
                method,
                parsed_doc.get("house_price"),
                len(parsed_doc.get("options") or []),
            )
        finally:
            if tmp_path is not None:
                tmp_path.unlink(missing_ok=True)

    document = merge_documents(structured, parsed_doc)
    project_id = payload.project_id
    if not project_id and document.get("project_name"):
        project_id = await match_project_id(session, document["project_name"])

    proposal = CommercialProposal(
        source=source,
        external_id=external_id or "",
        status=ProposalStatus.draft,
        project_id=project_id,
        request_payload=request_payload or structured,
        document=document,
        source_pdf_path="",
        intake_markdown=markdown,
    )
    session.add(proposal)
    await session.commit()
    await session.refresh(proposal)

    # One-shot hygiene for previously accumulated intake junk.
    removed = cleanup_intake_storage()
    if removed:
        logger.info("cleaned %s leftover intake file(s)", removed)

    return proposal


def document_from_payload(data: dict[str, Any]) -> dict[str, Any]:
    return normalize_document(data)
