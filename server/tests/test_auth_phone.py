from app.api.auth import _coerce_phone, _phone_from_profile


def test_phone_from_string_and_nested():
    assert _coerce_phone("+7 900 111-22-33") == "+7 900 111-22-33"
    assert _coerce_phone({"VALUE": "+7 900 000-00-00"}) == "+7 900 000-00-00"
    assert _coerce_phone([{"value": "+79991234567"}]) == "+79991234567"


def test_phone_from_profile_scans_uf_fields():
    profile = {
        "NAME": "Никита",
        "UF_USR_PHONE_MOBILE": [{"VALUE": "+7 930 000-11-22"}],
    }
    assert _phone_from_profile(profile) == "+7 930 000-11-22"
