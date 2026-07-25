import asyncio
import logging

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import require_user
from app.core.db import SessionLocal, get_db
from app.domain.schemas import SyncResult
from app.services.sync import sync_projects

router = APIRouter(dependencies=[Depends(require_user)])
logger = logging.getLogger(__name__)

_sync_lock = asyncio.Lock()


async def _run_sync_background() -> None:
    """Full Tilda sync with asset downloads — can take many minutes."""
    if _sync_lock.locked():
        logger.warning("Tilda sync already running, skip duplicate")
        return
    async with _sync_lock:
        try:
            async with SessionLocal() as session:
                result = await sync_projects(session)
                logger.info(
                    "Tilda sync done: created=%s updated=%s assets=%s errors=%s",
                    result.created,
                    result.updated,
                    result.assets_downloaded,
                    len(result.errors),
                )
        except Exception:
            logger.exception("Tilda background sync failed")


@router.post("/sync/tilda", response_model=SyncResult)
@router.post("/projects/sync", response_model=SyncResult)
async def sync_tilda(db: AsyncSession = Depends(get_db)) -> SyncResult:
    # Don't wait for asset downloads in HTTP — ngrok/browser will time out.
    _ = db
    if _sync_lock.locked():
        return SyncResult(
            status="started",
            message="Синхронизация уже выполняется. Обновите список проектов через пару минут.",
        )
    asyncio.create_task(_run_sync_background())
    return SyncResult(
        status="started",
        message="Синхронизация с Tilda запущена в фоне. Обновите список проектов через 1–3 минуты.",
    )
