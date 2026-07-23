"""Unit tests for Bitrix event → payload mapping (no network)."""

from app.services.bitrix_enrich import collect_file_candidates, extract_entity_ref, item_to_payload


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
        "ufCrm_photo": [{"id": 1, "name": "photo.jpg"}],
        "ufCrm_doc": [{"id": 2, "name": "smeta.pdf", "urlMachine": "https://x/a"}],
    }
    refs = collect_file_candidates(item)
    assert refs
    assert refs[0]["id"] == 2


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
