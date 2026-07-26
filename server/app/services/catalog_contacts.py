"""Контакты каталога: офис AVGST + менеджер из сессии Bitrix."""

from __future__ import annotations

from typing import Any, Optional

DEFAULT_SITE = "avgst.ru"

DEFAULT_OFFICE = {
    "city": "Нижний Новгород",
    "street": "проспект Гагарина, 27а к1",
    "building": "Деловой центр Ока",
    "floor": "11 этаж",
}


def manager_from_session(user: Optional[dict[str, Any]]) -> dict[str, str]:
    """Имя / телефон / email / фото текущего пользователя UI."""
    if not user:
        return {"name": "", "phone": "", "email": "", "photo": ""}
    name = " ".join(
        p for p in [str(user.get("name") or "").strip(), str(user.get("last_name") or "").strip()] if p
    ).strip()
    return {
        "name": name,
        "phone": str(user.get("phone") or "").strip(),
        "email": str(user.get("email") or "").strip(),
        "photo": str(user.get("photo") or "").strip(),
    }


def merge_catalog_contacts(
    contacts: Optional[dict[str, Any]],
    *,
    user: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    """Базовые контакты + офис + менеджер из сессии (если есть)."""
    base: dict[str, Any] = dict(contacts or {})
    if not base.get("site"):
        base["site"] = DEFAULT_SITE

    office = base.get("office")
    if not isinstance(office, dict) or not any(office.values()):
        base["office"] = dict(DEFAULT_OFFICE)
    else:
        merged_office = dict(DEFAULT_OFFICE)
        merged_office.update({k: v for k, v in office.items() if v})
        base["office"] = merged_office

    manager = manager_from_session(user)
    if any(manager.values()):
        base["manager"] = manager
    elif not isinstance(base.get("manager"), dict):
        base["manager"] = {"name": "", "phone": "", "email": "", "photo": ""}

    return base
