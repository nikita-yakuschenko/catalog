"""Bitrix24 OAuth → cookie-сессия UI каталога."""

from __future__ import annotations

import logging
import secrets
import time
from typing import Any, Optional
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Cookie, HTTPException, Query, Response
from fastapi.responses import JSONResponse, RedirectResponse

from app.core.config import settings
from app.core.session import (
    OAUTH_STATE_COOKIE,
    SESSION_COOKIE,
    make_session_token,
    sign_payload,
    unsign_payload,
)

router = APIRouter(prefix="/auth")
logger = logging.getLogger(__name__)


def _cookie_secure() -> bool:
    return settings.app_public_url.lower().startswith("https://")


def _portal_base() -> str:
    return settings.bitrix_portal_url.rstrip("/")


def _photo_from_profile(profile: dict[str, Any]) -> str:
    raw = profile.get("PERSONAL_PHOTO") or profile.get("personal_photo") or ""
    if isinstance(raw, str) and raw.startswith(("http://", "https://")):
        return raw
    return ""


def _phone_from_profile(profile: dict[str, Any]) -> str:
    for key in (
        "WORK_PHONE",
        "workPhone",
        "PERSONAL_MOBILE",
        "personalMobile",
        "PERSONAL_PHONE",
        "personalPhone",
    ):
        raw = profile.get(key)
        if isinstance(raw, str) and raw.strip():
            return raw.strip()
    return ""


def _user_payload(user: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": user.get("uid"),
        "name": user.get("name"),
        "last_name": user.get("last_name"),
        "email": user.get("email"),
        "photo": user.get("photo") or "",
        "phone": user.get("phone") or "",
    }


@router.get("/status")
async def get_auth_status(
    avgst_session: Optional[str] = Cookie(default=None, alias=SESSION_COOKIE),
) -> dict[str, Any]:
    enabled = settings.auth_enabled
    user = None
    if avgst_session:
        user = unsign_payload(avgst_session, settings.session_secret)
    elif not enabled:
        user = {"uid": "local", "name": "Local", "last_name": "Dev", "email": "", "photo": "", "phone": ""}
    return {
        "auth_enabled": enabled,
        "authenticated": bool(user),
        "user": _user_payload(user) if user else None,
    }


@router.get("/me")
async def me(avgst_session: Optional[str] = Cookie(default=None, alias=SESSION_COOKIE)) -> dict[str, Any]:
    if not settings.auth_enabled:
        return {"id": "local", "name": "Local", "last_name": "Dev", "email": "", "photo": "", "phone": ""}
    user = unsign_payload(avgst_session or "", settings.session_secret) if avgst_session else None
    if not user:
        raise HTTPException(401, "Не авторизован")
    return _user_payload(user)


@router.get("/bitrix/login")
async def bitrix_login() -> Response:
    if not settings.auth_enabled:
        raise HTTPException(400, "Bitrix OAuth не настроен (BITRIX_OAUTH_CLIENT_ID пуст)")
    if not settings.bitrix_oauth_client_secret.strip():
        raise HTTPException(500, "BITRIX_OAUTH_CLIENT_SECRET не задан")

    state = secrets.token_urlsafe(24)
    state_token = sign_payload({"state": state, "exp": time.time() + 600}, settings.session_secret)

    params = {
        "client_id": settings.bitrix_oauth_client_id.strip(),
        "state": state,
        "response_type": "code",
    }
    redirect_uri = settings.oauth_redirect_uri
    if redirect_uri:
        params["redirect_uri"] = redirect_uri

    url = f"{_portal_base()}/oauth/authorize/?{urlencode(params)}"
    response = RedirectResponse(url, status_code=302)
    response.set_cookie(
        OAUTH_STATE_COOKIE,
        state_token,
        httponly=True,
        secure=_cookie_secure(),
        samesite="lax",
        max_age=600,
        path="/",
    )
    return response


@router.get("/bitrix/callback")
async def bitrix_callback(
    code: Optional[str] = Query(default=None),
    state: Optional[str] = Query(default=None),
    domain: Optional[str] = Query(default=None),
    error: Optional[str] = Query(default=None),
    avgst_oauth_state: Optional[str] = Cookie(default=None, alias=OAUTH_STATE_COOKIE),
) -> Response:
    if error:
        logger.warning("bitrix oauth error=%s", error)
        raise HTTPException(400, f"Bitrix OAuth error: {error}")
    if not code or not state:
        raise HTTPException(400, "Нет code/state от Bitrix")

    saved = unsign_payload(avgst_oauth_state or "", settings.session_secret) if avgst_oauth_state else None
    if not saved or saved.get("state") != state:
        raise HTTPException(400, "Неверный OAuth state (повторите вход)")

    token_url = "https://oauth.bitrix24.tech/oauth/token/"
    token_params = {
        "grant_type": "authorization_code",
        "client_id": settings.bitrix_oauth_client_id.strip(),
        "client_secret": settings.bitrix_oauth_client_secret.strip(),
        "code": code,
    }
    async with httpx.AsyncClient(timeout=30.0) as client:
        token_resp = await client.get(token_url, params=token_params)
        try:
            token_data = token_resp.json()
        except Exception as exc:
            logger.exception("bitrix token non-json")
            raise HTTPException(502, f"Bitrix token: некорректный ответ ({exc})") from exc
        if token_resp.status_code >= 400 or token_data.get("error"):
            logger.warning("bitrix token failed: %s", token_data)
            raise HTTPException(
                502,
                f"Не удалось получить токен: {token_data.get('error_description') or token_data.get('error') or token_resp.status_code}",
            )

        access_token = token_data.get("access_token")
        if not access_token:
            raise HTTPException(502, "В ответе Bitrix нет access_token")

        client_endpoint = (token_data.get("client_endpoint") or "").rstrip("/")
        if not client_endpoint:
            portal_host = (domain or _portal_base().replace("https://", "").replace("http://", "")).strip("/")
            client_endpoint = f"https://{portal_host}/rest"

        user_resp = await client.post(
            f"{client_endpoint}/user.current",
            data={"auth": access_token},
        )
        try:
            user_payload = user_resp.json()
        except Exception as exc:
            raise HTTPException(502, f"user.current: некорректный ответ ({exc})") from exc
        if user_resp.status_code >= 400 or user_payload.get("error"):
            logger.warning("user.current failed: %s", user_payload)
            raise HTTPException(502, f"user.current failed: {user_payload.get('error_description') or user_payload}")

        profile = user_payload.get("result") or {}

    session_token = make_session_token(
        user_id=str(profile.get("ID") or ""),
        name=str(profile.get("NAME") or ""),
        last_name=str(profile.get("LAST_NAME") or ""),
        email=str(profile.get("EMAIL") or ""),
        photo=_photo_from_profile(profile),
        phone=_phone_from_profile(profile),
        secret=settings.session_secret,
        ttl_sec=settings.auth_session_ttl_sec,
    )

    dest = settings.app_public_url.rstrip("/") + "/"
    response = RedirectResponse(dest, status_code=302)
    response.set_cookie(
        SESSION_COOKIE,
        session_token,
        httponly=True,
        secure=_cookie_secure(),
        samesite="lax",
        max_age=settings.auth_session_ttl_sec,
        path="/",
    )
    response.delete_cookie(OAUTH_STATE_COOKIE, path="/")
    logger.info(
        "bitrix login ok user_id=%s name=%s %s",
        profile.get("ID"),
        profile.get("NAME"),
        profile.get("LAST_NAME"),
    )
    return response


@router.post("/logout")
async def logout() -> Response:
    response = JSONResponse({"ok": True})
    response.delete_cookie(SESSION_COOKIE, path="/")
    response.delete_cookie(OAUTH_STATE_COOKIE, path="/")
    return response
