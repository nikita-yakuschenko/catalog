"""Подписанная cookie-сессия UI (без внешних JWT-зависимостей)."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from typing import Any, Optional

SESSION_COOKIE = "avgst_session"
OAUTH_STATE_COOKIE = "avgst_oauth_state"


def _b64encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _b64decode(text: str) -> bytes:
    pad = "=" * (-len(text) % 4)
    return base64.urlsafe_b64decode(text + pad)


def sign_payload(payload: dict[str, Any], secret: str) -> str:
    body = _b64encode(json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8"))
    sig = hmac.new(secret.encode("utf-8"), body.encode("ascii"), hashlib.sha256).hexdigest()
    return f"{body}.{sig}"


def unsign_payload(token: str, secret: str) -> Optional[dict[str, Any]]:
    if not token or "." not in token:
        return None
    body, sig = token.rsplit(".", 1)
    expected = hmac.new(secret.encode("utf-8"), body.encode("ascii"), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, sig):
        return None
    try:
        data = json.loads(_b64decode(body).decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    exp = data.get("exp")
    if not isinstance(exp, (int, float)) or float(exp) < time.time():
        return None
    return data


def make_session_token(
    *,
    user_id: str,
    name: str,
    last_name: str,
    email: str,
    secret: str,
    ttl_sec: int,
    photo: str = "",
) -> str:
    now = int(time.time())
    return sign_payload(
        {
            "uid": str(user_id),
            "name": name or "",
            "last_name": last_name or "",
            "email": email or "",
            "photo": photo or "",
            "iat": now,
            "exp": now + int(ttl_sec),
        },
        secret,
    )
