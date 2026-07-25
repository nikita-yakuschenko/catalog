from app.services.bitrix_enrich import (
    collect_file_candidates,
    enumeration_map_from_fields,
    extract_entity_ref,
    item_to_payload,
    parse_bitrix_money,
    resolve_region_label,
    _file_refs_from_value,
)


def test_extract_entity_ref_from_dynamic_event():
    event = {
        "event": "ONCRMDYNAMICITEMADD",
        "data": {"FIELDS": {"ID": "25", "ENTITY_TYPE_ID": "1240"}},
    }
    entity_type_id, item_id = extract_entity_ref(event)
    assert entity_type_id == 1240
    assert item_id == 25


def test_collect_file_candidates_prefers_docs():
    item = {
        "ufCrm_photo": [{"id": 1, "name": "photo.jpg", "urlMachine": "https://x/p"}],
        "ufCrm_doc": [{"id": 2, "name": "smeta.pdf", "urlMachine": "https://x/a"}],
    }
    refs = collect_file_candidates(item)
    assert refs
    assert refs[0]["id"] == 2


def test_collect_file_candidates_ignores_region_enum_as_disk_id():
    """Регион=4499 не должен скачиваться как disk.file #4499 (баг КП #91)."""
    item = {
        "UF_CRM_129_1784903637": 4499,  # регион НН
        "UF_CRM_129_1784636008062": {
            "id": 464631,
            "name": "example2.pdf",
            "urlMachine": "https://bitrix/rest/getFile/example2",
        },
    }
    refs = collect_file_candidates(item, preferred_field="UF_CRM_129_1784636008062")
    assert refs
    assert refs[0]["name"] == "example2.pdf"
    assert refs[0]["id"] == 464631
    assert all(r.get("id") != 4499 for r in refs)


def test_collect_file_candidates_ignores_moscow_region_enum():
    """Московская область (4501) — тот же класс бага, что и 4499."""
    item = {
        "ufCrm129_1784903637": 4501,
        "UF_CRM_129_1784636008062": {
            "id": 1,
            "name": "smeta.pdf",
            "urlMachine": "https://x/smeta",
        },
    }
    refs = collect_file_candidates(item, preferred_field="UF_CRM_129_1784636008062")
    assert len(refs) == 1
    assert refs[0]["name"] == "smeta.pdf"
    assert all(r.get("id") != 4501 for r in refs)


def test_bare_int_never_file_ref_even_on_preferred_field():
    """Наглухо: голый ID в любом UF — не файл, даже в source-file поле."""
    assert _file_refs_from_value(4501) == []
    assert _file_refs_from_value("4499") == []
    assert _file_refs_from_value({"id": 99, "name": "x.pdf"}) == []  # нет URL
    item = {"UF_CRM_129_1784636008062": 464631}
    assert collect_file_candidates(item, preferred_field="UF_CRM_129_1784636008062") == []


def test_collect_file_candidates_skips_bare_int_uf_without_preferred():
    item = {
        "UF_CRM_129_1784903637": 4499,
        "UF_CRM_129_1784636008062": {
            "id": 10,
            "name": "smeta.pdf",
            "urlMachine": "https://x/smeta",
        },
    }
    refs = collect_file_candidates(item)
    assert len(refs) == 1
    assert refs[0]["name"] == "smeta.pdf"


def test_item_to_payload_maps_title_and_opportunity():
    payload = item_to_payload(
        event={"event": "ONCRMDYNAMICITEMADD"},
        item={"title": "Зимний 54", "opportunity": 2768000, "currencyId": "RUB", "contactId": 9},
        entity_type_id=1240,
        item_id=25,
        client_party={"name": "Иван", "phone": "+7", "email": "", "company": ""},
    )
    assert payload["deal_id"] == "25"
    assert payload["project_name"] == "Зимний 54"
    assert payload["house_price"] == 2768000
    assert payload["client"]["name"] == "Иван"
    assert payload["meta"]["bitrix"]["entity_type_id"] == 1240


def test_item_to_payload_region_and_delivery_money():
    payload = item_to_payload(
        event={},
        item={
            "title": "КП",
            "UF_CRM_129_1784903637": "4499",
            "UF_CRM_129_1784904416453": "120000|RUB",
        },
        entity_type_id=1240,
        item_id=1,
    )
    assert payload["region"] == "Нижегородская область"
    assert payload["delivery_price"] == 120000


def test_item_to_payload_uses_dynamic_region_map():
    payload = item_to_payload(
        event={},
        item={"UF_CRM_129_1784903637": "9999"},
        entity_type_id=1240,
        item_id=2,
        region_map={"9999": "Ленинградская область"},
    )
    assert payload["region"] == "Ленинградская область"


def test_parse_bitrix_money_and_region():
    assert parse_bitrix_money("85000|RUB") == 85000
    assert parse_bitrix_money(0) is None
    assert resolve_region_label("4501") == "Московская область"
    assert resolve_region_label("Московская область") == "Московская область"
    assert resolve_region_label("7777") is None  # неизвестный enum id не светим
    assert resolve_region_label("8888", {"8888": "Казань"}) == "Казань"


def test_enumeration_map_from_fields():
    fields = {
        "UF_CRM_129_1784903637": {
            "type": "enumeration",
            "items": [
                {"ID": "4499", "VALUE": "Нижегородская область"},
                {"ID": "4501", "VALUE": "Московская область"},
                {"ID": "9999", "VALUE": "Новый регион"},
            ],
        }
    }
    mapping = enumeration_map_from_fields(fields, "UF_CRM_129_1784903637")
    assert mapping["9999"] == "Новый регион"
    assert mapping["4501"] == "Московская область"
