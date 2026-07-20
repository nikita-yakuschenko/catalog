from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import SessionLocal, get_db
from app.domain.schemas import SyncResult
from app.services.sync import sync_projects

router = APIRouter()


async def _run_sync() -> SyncResult:
    async with SessionLocal() as session:
        return await sync_projects(session)


@router.post("/sync/tilda", response_model=SyncResult)
@router.post("/projects/sync", response_model=SyncResult)
async def sync_tilda(background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)) -> SyncResult:
    # Sync inline for MVP reliability (assets download can take time)
    return await sync_projects(db)
