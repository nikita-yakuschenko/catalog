"""Контакты каталога: офис AVGST + менеджер из сессии Bitrix."""

from __future__ import annotations

from typing import Any, Optional

DEFAULT_SITE = "avgst.ru"

DEFAULT_OFFICE = {
    "city": "Нижний Новгород",
    "street": "проспект Гагарина, 27а к1",
    "building": "Деловой центр Ока",
    "floor": "11-й этаж",
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

    # Офис AVGST фиксированный
    base["office"] = dict(DEFAULT_OFFICE)

    incoming = manager_from_session(user)
    previous = base.get("manager") if isinstance(base.get("manager"), dict) else {}
    if any(incoming.values()) or any(str(previous.get(k) or "") for k in ("name", "phone", "email", "photo")):
        # Новые непустые поля из сессии, иначе оставляем ранее сохранённые
        base["manager"] = {
            "name": incoming.get("name") or previous.get("name") or "",
            "phone": incoming.get("phone") or previous.get("phone") or "",
            "email": incoming.get("email") or previous.get("email") or "",
            "photo": incoming.get("photo") or previous.get("photo") or "",
        }
    else:
        base["manager"] = {"name": "", "phone": "", "email": "", "photo": ""}

    return base
