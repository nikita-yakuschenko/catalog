from app.services.catalog_contacts import DEFAULT_OFFICE, merge_catalog_contacts


def test_merge_contacts_adds_office_and_manager():
    contacts = merge_catalog_contacts(
        {"site": "avgst.ru"},
        user={
            "name": "Никита",
            "last_name": "Якушенко",
            "email": "n@avgst.ru",
            "phone": "+7 900 111-22-33",
            "photo": "https://cdn.example/a.jpg",
        },
    )
    assert contacts["site"] == "avgst.ru"
    assert contacts["office"] == DEFAULT_OFFICE
    assert contacts["manager"]["name"] == "Никита Якушенко"
    assert contacts["manager"]["phone"] == "+7 900 111-22-33"
    assert contacts["manager"]["photo"] == "https://cdn.example/a.jpg"


def test_merge_contacts_keeps_previous_phone_if_session_empty():
    contacts = merge_catalog_contacts(
        {"manager": {"name": "Никита", "phone": "+7 900 000-00-00", "email": "", "photo": ""}},
        user={
            "name": "Никита",
            "last_name": "Якушенко",
            "email": "n@avgst.ru",
            "phone": "",
            "photo": "",
        },
    )
    assert contacts["manager"]["phone"] == "+7 900 000-00-00"
    assert contacts["manager"]["name"] == "Никита Якушенко"
    assert contacts["office"]["floor"] == "11-й этаж"
