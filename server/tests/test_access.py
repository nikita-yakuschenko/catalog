from types import SimpleNamespace

from app.core.access import can_access_catalog, can_access_proposal


def test_admin_sees_all_catalogs():
    admin = {"uid": "1", "is_admin": True, "email": "a@x.ru"}
    foreign = SimpleNamespace(contacts={"manager": {"id": "99", "email": "other@x.ru"}})
    assert can_access_catalog(foreign, admin)


def test_manager_sees_own_catalog_by_id():
    user = {"uid": "42", "is_admin": False, "email": "me@x.ru"}
    own = SimpleNamespace(contacts={"manager": {"id": "42", "email": "me@x.ru"}})
    other = SimpleNamespace(contacts={"manager": {"id": "7", "email": "o@x.ru"}})
    assert can_access_catalog(own, user)
    assert not can_access_catalog(other, user)


def test_legacy_catalog_without_owner_visible():
    user = {"uid": "42", "is_admin": False, "email": "me@x.ru"}
    legacy = SimpleNamespace(contacts={"manager": {"name": "Кто-то"}})
    assert can_access_catalog(legacy, user)


def test_admin_sees_all_proposals():
    admin = {"uid": "1", "is_admin": True, "email": "a@x.ru"}
    foreign = SimpleNamespace(
        document={"manager": {"id": "9"}, "meta": {"bitrix": {"assigned_by_id": 9}}}
    )
    assert can_access_proposal(foreign, admin)


def test_manager_sees_own_proposal_by_assigned():
    user = {"uid": "42", "is_admin": False, "email": "me@x.ru"}
    own = SimpleNamespace(document={"manager": {}, "meta": {"bitrix": {"assigned_by_id": 42}}})
    other = SimpleNamespace(document={"manager": {}, "meta": {"bitrix": {"assigned_by_id": 7}}})
    assert can_access_proposal(own, user)
    assert not can_access_proposal(other, user)
