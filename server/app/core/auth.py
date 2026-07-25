"""Зависимости авторизации UI."""

from __future__ import annotations

from typing import Any, Optional

from fastapi import Cookie, HTTPException, Request

from app.core.config import settings
from app.core.session import SESSION_COOKIE, unsign_payload


def read_session_user(
    avgst_session: Optional[str] = Cookie(default=None, alias=SESSION_COOKIE),
) -> Optional[dict[str, Any]]:
    if not avgst_session:
        return None
    return unsign_payload(avgst_session, settings.session_secret)


def require_user(
    request: Request,
    avgst_session: Optional[str] = Cookie(default=None, alias=SESSION_COOKIE),
) -> dict[str, Any]:
    """Требует сессию, если OAuth включён. Иначе пропускает (локальная разработка)."""
    if not settings.auth_enabled:
        return {"uid": "local", "name": "Local", "last_name": "Dev", "email": ""}

    user = unsign_payload(avgst_session or "", settings.session_secret) if avgst_session else None
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Требуется вход через Bitrix24",
            headers={"WWW-Authenticate": "Bitrix24"},
        )
    return user
