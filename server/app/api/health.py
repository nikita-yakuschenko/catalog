from fastapi import APIRouter, Response, status

from app.core.db import ping_database

router = APIRouter()


@router.get("/health")
async def health(response: Response) -> dict[str, str]:
    if not await ping_database():
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {"status": "unavailable"}
    return {"status": "ok"}
