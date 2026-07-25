"""Enrich Bitrix outbound webhook with CRM item + Disk source file."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from app.core.config import settings
from app.services.bitrix_rest import BitrixRestClient, BitrixRestError

logger = logging.getLogger(__name__)

DOC_EXTS = {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".txt", ".md", ".rtf", ".odt"}


@dataclass
class BitrixEnrichment:
    payload: dict[str, Any]
    pdf_bytes: Optional[bytes] = None
    pdf_filename: str = "source.pdf"
    warnings: list[str] = field(default_factory=list)
    item: dict[str, Any] = field(default_factory=dict)
    entity_type_id: Optional[int] = None
    item_id: Optional[int] = None
    source_disk_file_id: Optional[int] = None
    source_parent_folder_id: Optional[int] = None


def _as_str(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _as_int(value: Any) -> Optional[int]:
    if value is None or value == "":
        return None
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


def _item_field(item: dict[str, Any], *candidates: str) -> Any:
    """Read UF by original (UF_CRM_…) or camelCase (ufCrm…) name."""
    for key in candidates:
        if key in item and item[key] not in (None, "", []):
            return item[key]
    lower_map = {str(k).lower(): v for k, v in item.items()}
    for key in candidates:
        value = lower_map.get(key.lower())
        if value not in (None, "", []):
            return value
    return None


# Регион поставки (строительства) — enum ID → подпись
_REGION_BY_ID = {
    "4499": "Нижегородская область",
    "4501": "Московская область",
    "4503": "Другое",
}


def parse_bitrix_money(raw: Any) -> Optional[int]:
    """Bitrix money UF: '150000|RUB', {'amount': …}, or plain number → rubles int."""
    if raw in (None, "", [], {}, 0, "0"):
        return None
    if isinstance(raw, dict):
        raw = raw.get("amount") or raw.get("VALUE") or raw.get("value") or raw.get("sum")
    text = str(raw).strip()
    if "|" in text:
        text = text.split("|", 1)[0].strip()
    text = text.replace(" ", "").replace("\u00a0", "").replace(",", ".")
    try:
        amount = float(text)
    except ValueError:
        return None
    if amount <= 0:
        return None
    return int(round(amount))


def resolve_region_label(raw: Any) -> Optional[str]:
    """Map Bitrix enumeration id/value to region title."""
    if raw in (None, "", [], {}):
        return None
    if isinstance(raw, list) and raw:
        raw = raw[0]
    if isinstance(raw, dict):
        raw = raw.get("value") or raw.get("VALUE") or raw.get("id") or raw.get("ID")
    text = _as_str(raw)
    if not text:
        return None
    if text in _REGION_BY_ID:
        return _REGION_BY_ID[text]
    low = text.lower()
    for label in _REGION_BY_ID.values():
        if label.lower() == low:
            return label
    return text


def _dig(data: dict[str, Any], *path: str) -> Any:
    cur: Any = data
    for key in path:
        if not isinstance(cur, dict) or key not in cur:
            return None
        cur = cur[key]
    return cur


def extract_entity_ref(event: dict[str, Any]) -> tuple[Optional[int], Optional[int]]:
    fields = _dig(event, "data", "FIELDS") or _dig(event, "data", "fields") or {}
    if not isinstance(fields, dict):
        fields = {}
    entity_type_id = _as_int(
        fields.get("ENTITY_TYPE_ID")
        or fields.get("entityTypeId")
        or event.get("entityTypeId")
        or event.get("ENTITY_TYPE_ID")
    )
    item_id = _as_int(
        fields.get("ID")
        or fields.get("id")
        or event.get("deal_id")
        or event.get("ID")
        or _dig(event, "data", "id")
    )
    return entity_type_id, item_id


def _phone_email_from_fm(fm: Any) -> tuple[str, str]:
    phone = ""
    email = ""
    if not isinstance(fm, list):
        return phone, email
    for row in fm:
        if not isinstance(row, dict):
            continue
        typ = str(row.get("TYPE_ID") or row.get("typeId") or "").upper()
        val = _as_str(row.get("VALUE") or row.get("value"))
        if typ == "PHONE" and not phone:
            phone = val
        elif typ == "EMAIL" and not email:
            email = val
    return phone, email


def _multi_field_value(value: Any) -> str:
    """Bitrix PHONE/EMAIL fields are often lists of {VALUE, TYPE_ID}."""
    if isinstance(value, list) and value:
        first = value[0]
        if isinstance(first, dict):
            return _as_str(first.get("VALUE") or first.get("value"))
        return _as_str(first)
    if isinstance(value, dict):
        return _as_str(value.get("VALUE") or value.get("value"))
    if isinstance(value, (list, dict)):
        return ""
    return _as_str(value)


def _contact_party(contact: dict[str, Any]) -> dict[str, str]:
    name = " ".join(
        p
        for p in [
            _as_str(contact.get("NAME") or contact.get("name")),
            _as_str(contact.get("SECOND_NAME") or contact.get("secondName")),
            _as_str(contact.get("LAST_NAME") or contact.get("lastName")),
        ]
        if p
    ).strip()
    phone, email = _phone_email_from_fm(contact.get("FM") or contact.get("fm"))
    if not phone:
        phone = _multi_field_value(contact.get("PHONE") or contact.get("phone"))
    if not email:
        email = _multi_field_value(contact.get("EMAIL") or contact.get("email"))
    return {
        "name": name,
        "company": _as_str(contact.get("COMPANY_TITLE") or contact.get("companyTitle")),
        "phone": phone,
        "email": email,
    }


def _manager_party(user: dict[str, Any]) -> dict[str, str]:
    name = " ".join(
        p
        for p in [
            _as_str(user.get("NAME") or user.get("name")),
            _as_str(user.get("LAST_NAME") or user.get("lastName")),
        ]
        if p
    ).strip() or _as_str(user.get("EMAIL") or user.get("email"))
    return {
        "name": name,
        "company": "",
        "phone": _as_str(user.get("WORK_PHONE") or user.get("workPhone") or user.get("PERSONAL_MOBILE")),
        "email": _as_str(user.get("EMAIL") or user.get("email")),
    }


def _looks_like_doc_name(name: str) -> bool:
    return Path(name).suffix.lower() in DOC_EXTS


def _non_file_uf_fields() -> set[str]:
    """UF that must never be treated as source documents."""
    return {
        f.strip()
        for f in (
            settings.bitrix_region_field,
            settings.bitrix_delivery_price_field,
            settings.bitrix_result_file_field,
        )
        if f and f.strip()
    }


def _file_refs_from_value(value: Any, *, allow_bare_id: bool = False) -> list[dict[str, Any]]:
    """Normalize Bitrix UF file values into {id?, url?, name?} dicts.

    Bare integers (enumeration IDs like region=4499) are NOT file refs unless
    allow_bare_id=True for an explicitly configured source-file field.
    """
    out: list[dict[str, Any]] = []
    if value in (None, "", [], {}):
        return out
    if isinstance(value, (int, float)) or (isinstance(value, str) and value.strip().isdigit()):
        if allow_bare_id:
            out.append({"id": int(value)})
        return out
    if isinstance(value, str) and value.startswith("http"):
        out.append({"url": value, "name": value.rsplit("/", 1)[-1]})
        return out
    if isinstance(value, dict):
        fid = _as_int(value.get("id") or value.get("ID") or value.get("fileId") or value.get("FILE_ID"))
        url = (
            value.get("urlMachine")
            or value.get("urlDownload")
            or value.get("downloadUrl")
            or value.get("DOWNLOAD_URL")
            or value.get("url")
            or value.get("showUrl")
        )
        name = _as_str(value.get("name") or value.get("NAME") or value.get("fileName"))
        # Real CRM file objects always expose urlMachine/url; bare {id: N} is not enough
        if url or (fid and name):
            out.append({"id": fid, "url": url, "name": name})
        return out
    if isinstance(value, list):
        for item in value:
            out.extend(_file_refs_from_value(item, allow_bare_id=allow_bare_id))
    return out


def collect_file_candidates(item: dict[str, Any], preferred_field: str = "") -> list[dict[str, Any]]:
    preferred = preferred_field.strip()
    skip_fields = _non_file_uf_fields()
    candidates: list[dict[str, Any]] = []

    def add_from(field: str, value: Any, *, priority: int, allow_bare_id: bool = False) -> None:
        for ref in _file_refs_from_value(value, allow_bare_id=allow_bare_id):
            name = _as_str(ref.get("name"))
            url = _as_str(ref.get("url"))
            # Prefer real CRM download URLs over Disk id guesses
            score = priority
            if url:
                score -= 5
            if name and _looks_like_doc_name(name):
                score -= 2
            elif name and not _looks_like_doc_name(name):
                score += 50
            elif not name and not url:
                # bare id only — last resort
                score += 80
            ref["priority"] = score
            ref["field"] = field
            candidates.append(ref)

    if preferred and preferred in item:
        add_from(preferred, item.get(preferred), priority=0, allow_bare_id=True)

    for key, value in item.items():
        key_l = key.lower()
        if preferred and key == preferred:
            continue
        if key in skip_fields:
            continue
        if key_l.startswith("uf") or "file" in key_l or key_l in {"files", "documents"}:
            add_from(key, value, priority=10, allow_bare_id=False)

    candidates.sort(key=lambda r: int(r.get("priority") or 99))
    return candidates


def _guess_filename(name: str, content: bytes) -> str:
    if name and _looks_like_doc_name(name):
        return name
    if content[:4] == b"%PDF":
        return (Path(name).stem if name else "source") + ".pdf"
    if content[:2] == b"PK":
        return (Path(name).stem if name else "source") + ".docx"
    return name or "source.bin"


async def _download_first_doc(
    client: BitrixRestClient, candidates: list[dict[str, Any]]
) -> tuple[Optional[bytes], str, Optional[int], Optional[int], list[str]]:
    warnings: list[str] = []
    for ref in candidates:
        try:
            fid = _as_int(ref.get("id"))
            url = _as_str(ref.get("url"))
            name = _as_str(ref.get("name")) or "source.bin"
            parent_id: Optional[int] = None

            # CRM UF files expose urlMachine; id is NOT always a Disk file id.
            if url:
                content = await client.download_url(url)
                name = _guess_filename(name, content)
                return content, name, fid, parent_id, warnings

            if fid:
                meta = await client.get_disk_file(fid)
                parent_id = _as_int(meta.get("PARENT_ID") or meta.get("parentId"))
                name = _as_str(meta.get("NAME") or meta.get("name") or name) or f"file-{fid}"
                download = _as_str(meta.get("DOWNLOAD_URL") or meta.get("downloadUrl"))
                if not download:
                    warnings.append(f"file #{fid}: нет DOWNLOAD_URL")
                    continue
                if not _looks_like_doc_name(name) and any(
                    _looks_like_doc_name(_as_str(c.get("name"))) for c in candidates
                ):
                    continue
                content = await client.download_url(download)
                name = _guess_filename(name, content)
                return content, name, fid, parent_id, warnings
        except Exception as exc:
            warnings.append(f"download failed: {exc}")
            logger.warning("bitrix source download failed: %s", exc)
    return None, "source.pdf", None, None, warnings


def item_to_payload(
    *,
    event: dict[str, Any],
    item: dict[str, Any],
    entity_type_id: int,
    item_id: int,
    client_party: Optional[dict[str, str]] = None,
    manager_party: Optional[dict[str, str]] = None,
    linked_project: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    title = _as_str(item.get("title") or item.get("TITLE") or item.get("name") or item.get("NAME"))
    linked = linked_project or {}
    linked_title = _as_str(linked.get("title") or linked.get("TITLE") or "")
    # Prefer База проектов title over generic "Коммерческое предложение #N"
    project_name = linked_title or _as_str(
        item.get("ufCrmProjectName")
        or item.get("UF_CRM_PROJECT_NAME")
        or item.get("project_name")
        or title
    )
    package_name = item.get("package_name") or item.get("UF_CRM_PACKAGE") or item.get("ufCrmPackage")
    # Prices come from estimate PDF (MarkItDown); Bitrix opportunity is only a fallback.
    opportunity = item.get("opportunity") if item.get("opportunity") is not None else item.get("OPPORTUNITY")
    house_price = None
    if opportunity not in (None, "", 0, "0"):
        try:
            house_price = int(float(str(opportunity).replace(" ", "").replace(",", ".")))
        except ValueError:
            house_price = None

    region_field = settings.bitrix_region_field.strip()
    delivery_field = settings.bitrix_delivery_price_field.strip()
    region_keys = [region_field, "ufCrm129_1784903637", "UF_CRM_129_1784903637"]
    delivery_keys = [delivery_field, "ufCrm129_1784904416453", "UF_CRM_129_1784904416453"]
    region = resolve_region_label(_item_field(item, *[k for k in region_keys if k]))
    delivery_price = parse_bitrix_money(_item_field(item, *[k for k in delivery_keys if k]))

    currency = _as_str(item.get("currencyId") or item.get("CURRENCY_ID") or "RUB") or "RUB"
    notes = _as_str(item.get("comments") or item.get("COMMENTS") or "")

    contact_id = _as_int(item.get("contactId") or item.get("CONTACT_ID"))
    if not contact_id:
        ids = item.get("contactIds") or item.get("CONTACT_IDS") or []
        if isinstance(ids, list) and ids:
            contact_id = _as_int(ids[0])

    parent_key = f"parentId{settings.bitrix_project_entity_type_id}"
    return {
        "deal_id": str(item_id),
        "lead_id": None,
        "contact_id": str(contact_id) if contact_id else None,
        "project_name": project_name,
        "package_name": _as_str(package_name) or None,
        "house_price": house_price,
        "region": region,
        "delivery_price": delivery_price,
        "currency": currency,
        "notes": notes,
        "options": [],
        "client": client_party or {},
        "manager": manager_party or {},
        "meta": {
            "bitrix": {
                "entity_type_id": entity_type_id,
                "item_id": item_id,
                "title": title,
                "stage_id": item.get("stageId") or item.get("STAGE_ID"),
                "parent_project_entity_type_id": settings.bitrix_project_entity_type_id,
                "parent_project_id": _as_int(item.get(parent_key) or linked.get("id")),
                "parent_project_title": linked_title or None,
                "assigned_by_id": _as_int(item.get("assignedById") or item.get("ASSIGNED_BY_ID")),
                "region": region,
                "delivery_price": delivery_price,
            }
        },
        "raw": {"event": event, "item": item, "linked_project": linked or None},
    }


async def _resolve_linked_project(
    client: BitrixRestClient, item: dict[str, Any]
) -> tuple[Optional[dict[str, Any]], list[str]]:
    """Resolve parentId{База проектов} → real project title (not just the numeric id)."""
    warnings: list[str] = []
    entity_type_id = int(settings.bitrix_project_entity_type_id or 0)
    if not entity_type_id:
        return None, warnings
    parent_key = f"parentId{entity_type_id}"
    parent_id = _as_int(item.get(parent_key) or item.get(f"PARENT_ID_{entity_type_id}"))
    if not parent_id:
        warnings.append(f"Нет связи {parent_key} с Базой проектов")
        return None, warnings
    try:
        linked = await client.get_item(entity_type_id, parent_id)
        logger.info(
            "bitrix linked project entity=%s id=%s title=%s",
            entity_type_id,
            parent_id,
            linked.get("title"),
        )
        return linked, warnings
    except Exception as exc:
        warnings.append(f"База проектов #{parent_id}: {exc}")
        logger.warning("bitrix linked project fetch failed: %s", exc)
        return None, warnings


async def enrich_bitrix_event(event: dict[str, Any]) -> BitrixEnrichment:
    """Fetch SPA/CRM item, optional contact/user, download first document from Disk/UF."""
    entity_type_id, item_id = extract_entity_ref(event)
    base_payload = {
        "deal_id": _as_str(item_id or ""),
        "project_name": "",
        "raw": event,
        "meta": {},
        "client": {},
        "manager": {},
        "options": [],
        "currency": "RUB",
        "notes": "",
        "package_name": None,
        "house_price": None,
        "lead_id": None,
        "contact_id": None,
    }

    if not settings.bitrix_rest_webhook_url.strip():
        return BitrixEnrichment(payload=base_payload, warnings=["BITRIX_REST_WEBHOOK_URL пуст"])

    if not entity_type_id or not item_id:
        return BitrixEnrichment(
            payload=base_payload,
            warnings=["В событии нет entityTypeId/id — обогащение пропущено"],
        )

    client = BitrixRestClient()
    warnings: list[str] = []
    try:
        item = await client.get_item(entity_type_id, item_id)
    except BitrixRestError as exc:
        logger.exception("bitrix crm.item.get failed")
        base_payload["meta"] = {"bitrix_error": str(exc)}
        return BitrixEnrichment(
            payload=base_payload,
            warnings=[str(exc)],
            entity_type_id=entity_type_id,
            item_id=item_id,
        )

    linked_project, link_warnings = await _resolve_linked_project(client, item)
    warnings.extend(link_warnings)

    client_party: dict[str, str] = {}
    contact_id = _as_int(item.get("contactId") or item.get("CONTACT_ID"))
    if not contact_id:
        ids = item.get("contactIds") or item.get("CONTACT_IDS") or []
        if isinstance(ids, list) and ids:
            contact_id = _as_int(ids[0])
    if contact_id:
        try:
            client_party = _contact_party(await client.get_contact(contact_id))
        except Exception as exc:
            warnings.append(f"contact: {exc}")

    manager_party: dict[str, str] = {}
    assigned = _as_int(item.get("assignedById") or item.get("ASSIGNED_BY_ID"))
    if assigned:
        try:
            manager_party = _manager_party(await client.get_user(assigned))
        except Exception as exc:
            warnings.append(f"user: {exc}")

    payload = item_to_payload(
        event=event,
        item=item,
        entity_type_id=entity_type_id,
        item_id=item_id,
        client_party=client_party,
        manager_party=manager_party,
        linked_project=linked_project,
    )

    preferred = settings.bitrix_source_file_field.strip()
    candidates = collect_file_candidates(item, preferred_field=preferred)
    pdf_bytes, filename, disk_id, parent_id, dl_warnings = await _download_first_doc(client, candidates)
    warnings.extend(dl_warnings)
    if not pdf_bytes:
        warnings.append("Исходный файл на Диске/в UF не найден")

    meta = dict(payload.get("meta") or {})
    bitrix_meta = dict(meta.get("bitrix") or {})
    bitrix_meta.update(
        {
            "source_disk_file_id": disk_id,
            "source_parent_folder_id": parent_id,
            "source_filename": filename,
            "warnings": warnings,
        }
    )
    meta["bitrix"] = bitrix_meta
    payload["meta"] = meta

    logger.info(
        "bitrix enrich entity=%s id=%s project=%s file=%s warnings=%s",
        entity_type_id,
        item_id,
        payload.get("project_name"),
        filename if pdf_bytes else None,
        warnings,
    )
    return BitrixEnrichment(
        payload=payload,
        pdf_bytes=pdf_bytes,
        pdf_filename=filename,
        warnings=warnings,
        item=item,
        entity_type_id=entity_type_id,
        item_id=item_id,
        source_disk_file_id=disk_id,
        source_parent_folder_id=parent_id,
    )


async def set_item_stage(
    *,
    entity_type_id: int,
    item_id: int,
    stage_id: str,
) -> dict[str, Any]:
    """Move SPA item to a pipeline stage (e.g. Подготовка КП)."""
    stage = (stage_id or "").strip()
    if not stage:
        return {"skipped": True, "reason": "empty stage"}
    if not settings.bitrix_rest_webhook_url.strip():
        return {"skipped": True, "reason": "no webhook url"}
    client = BitrixRestClient()
    updated = await client.update_item_fields(
        int(entity_type_id),
        int(item_id),
        {"stageId": stage},
    )
    logger.info("bitrix stage set entity=%s id=%s stage=%s", entity_type_id, item_id, stage)
    return {"stage_id": stage, "item_update": updated}


async def upload_proposal_pdf(
    *,
    pdf_path: Path,
    entity_type_id: Optional[int],
    item_id: Optional[int],
    parent_folder_id: Optional[int],
    opportunity: Optional[int] = None,
    project_name: str = "",
    assigned_by_id: Optional[int] = None,
) -> dict[str, Any]:
    """Upload KP PDF, set opportunity + ready stage, notify manager."""
    import base64

    if not settings.bitrix_rest_webhook_url.strip():
        return {"skipped": True, "reason": "no webhook url"}
    if not entity_type_id or not item_id:
        return {"skipped": True, "reason": "no bitrix item ref"}

    client = BitrixRestClient()
    content = pdf_path.read_bytes()
    filename = f"KP-{item_id}.pdf"
    result: dict[str, Any] = {}
    fields: dict[str, Any] = {}

    result_field = settings.bitrix_result_file_field.strip()
    if result_field:
        fields[result_field] = [filename, base64.b64encode(content).decode("ascii")]

    if opportunity is not None:
        fields["opportunity"] = int(opportunity)
        fields["isManualOpportunity"] = "Y"
        result["opportunity"] = int(opportunity)

    stage_id = settings.bitrix_ready_stage_id.strip()
    if stage_id:
        fields["stageId"] = stage_id
        result["stage_id"] = stage_id

    if fields:
        updated = await client.update_item_fields(int(entity_type_id), int(item_id), fields)
        result["item_field_updated"] = result_field or None
        result["item_update"] = updated
        logger.info(
            "bitrix KP published entity=%s id=%s opportunity=%s stage=%s file=%s",
            entity_type_id,
            item_id,
            opportunity,
            stage_id or None,
            bool(result_field),
        )

    folder_id = _as_int(settings.bitrix_kp_folder_id) or parent_folder_id
    if folder_id:
        uploaded = await client.upload_folder_file(folder_id, filename, content)
        result["disk_uploaded"] = uploaded
        result["folder_id"] = folder_id

    # Resolve manager if not provided
    manager_id = _as_int(assigned_by_id)
    if not manager_id:
        try:
            item = await client.get_item(int(entity_type_id), int(item_id))
            manager_id = _as_int(item.get("assignedById") or item.get("ASSIGNED_BY_ID"))
        except Exception as exc:
            result["manager_lookup_error"] = str(exc)

    amount_text = f"{int(opportunity):,}".replace(",", " ") + " руб." if opportunity is not None else "—"
    title = project_name.strip() or f"элемент #{item_id}"
    notify_message = (
        f"КП готово: [b]{title}[/b]\n"
        f"Сумма: [b]{amount_text}[/b]\n"
        f"Стадия: КП Готово\n"
        f"Файл загружен в карточку #{item_id}."
    )

    # Bell notification (requires webhook scope «Чат и уведомления» / im)
    if manager_id:
        try:
            notify_id = await client.call(
                "im.notify.system.add",
                {
                    "USER_ID": manager_id,
                    "MESSAGE": notify_message,
                    "TAG": f"KP_READY_{entity_type_id}_{item_id}",
                },
            )
            result["notify_id"] = notify_id
            result["notify_user_id"] = manager_id
        except Exception as exc:
            result["notify_error"] = str(exc)
            logger.warning("bitrix im.notify failed: %s", exc)

    # Always leave a timeline trail (crm scope)
    try:
        comment_id = await client.call(
            "crm.timeline.comment.add",
            {
                "fields": {
                    "ENTITY_ID": int(item_id),
                    "ENTITY_TYPE": f"dynamic_{int(entity_type_id)}",
                    "COMMENT": notify_message,
                }
            },
        )
        result["timeline_comment_id"] = comment_id
    except Exception as exc:
        result["timeline_error"] = str(exc)
        logger.warning("bitrix timeline comment failed: %s", exc)

    if not result:
        return {"skipped": True, "reason": "nothing to publish"}
    return result
