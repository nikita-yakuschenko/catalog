"""Create and enrich commercial proposals."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.domain.models import CommercialProposal, HouseProject, ProposalSource, ProposalStatus
from app.domain.schemas import ProposalCreate
from app.services.proposal_intake import pdf_to_markdown
from app.services.proposal_parse import merge_documents, normalize_document, parse_markdown


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
        storage = Path(settings.storage_dir) / "proposals" / "intake"
        storage.mkdir(parents=True, exist_ok=True)
        pdf_path = storage / f"{uuid4()}_{pdf_filename}"
        pdf_path.write_bytes(pdf_bytes)
        markdown = pdf_to_markdown(pdf_path)
        parsed_doc = parse_markdown(markdown)
        source_pdf_path = str(pdf_path)
    else:
        source_pdf_path = ""

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
        source_pdf_path=source_pdf_path,
        intake_markdown=markdown,
    )
    session.add(proposal)
    await session.commit()
    await session.refresh(proposal)
    return proposal


def document_from_payload(data: dict[str, Any]) -> dict[str, Any]:
    return normalize_document(data)
