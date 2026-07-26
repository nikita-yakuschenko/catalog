"""Правила видимости: админ видит всё, менеджер — только своё."""

from __future__ import annotations

from typing import Any, Optional


def is_admin(user: Optional[dict[str, Any]]) -> bool:
    return bool(user and user.get("is_admin"))


def user_uid(user: Optional[dict[str, Any]]) -> str:
    if not user:
        return ""
    return str(user.get("uid") or "").strip()


def _norm_email(value: Any) -> str:
    return str(value or "").strip().lower()


def _manager_matches(manager: Any, user: dict[str, Any]) -> bool:
    if not isinstance(manager, dict):
        return False
    uid = user_uid(user)
    mid = str(manager.get("id") or "").strip()
    if uid and mid and uid == mid:
        return True
    # Старые записи без id — по email
    memail = _norm_email(manager.get("email"))
    uemail = _norm_email(user.get("email"))
    return bool(memail and uemail and memail == uemail)


def _has_owner_marker(manager: Any) -> bool:
    if not isinstance(manager, dict):
        return False
    return bool(str(manager.get("id") or "").strip() or str(manager.get("email") or "").strip())


def can_access_catalog(catalog: Any, user: dict[str, Any]) -> bool:
    if is_admin(user):
        return True
    contacts = getattr(catalog, "contacts", None) or {}
    if not isinstance(contacts, dict):
        return True
    manager = contacts.get("manager")
    # Без владельца — общая запись (старые каталоги)
    if not _has_owner_marker(manager):
        return True
    return _manager_matches(manager, user)


def can_access_proposal(proposal: Any, user: dict[str, Any]) -> bool:
    if is_admin(user):
        return True
    doc = getattr(proposal, "document", None) or {}
    if not isinstance(doc, dict):
        return True
    manager = doc.get("manager")
    meta = doc.get("meta") if isinstance(doc.get("meta"), dict) else {}
    bitrix = meta.get("bitrix") if isinstance(meta.get("bitrix"), dict) else {}
    assigned = str(bitrix.get("assigned_by_id") or "").strip()
    has_owner = _has_owner_marker(manager) or bool(assigned)
    if not has_owner:
        return True
    if _manager_matches(manager, user):
        return True
    uid = user_uid(user)
    return bool(uid and assigned and uid == assigned)
