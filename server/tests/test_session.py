from app.core.session import make_session_token, unsign_payload


def test_session_roundtrip():
    token = make_session_token(
        user_id="42",
        name="Иван",
        last_name="Иванов",
        email="ivan@example.com",
        photo="https://cdn.example/photo.jpg",
        phone="+7 900 000-00-00",
        secret="test-secret",
        ttl_sec=3600,
    )
    data = unsign_payload(token, "test-secret")
    assert data is not None
    assert data["uid"] == "42"
    assert data["name"] == "Иван"
    assert data["email"] == "ivan@example.com"
    assert data["photo"] == "https://cdn.example/photo.jpg"
    assert data["phone"] == "+7 900 000-00-00"


def test_session_rejects_bad_secret():
    token = make_session_token(
        user_id="1",
        name="A",
        last_name="B",
        email="",
        secret="right",
        ttl_sec=3600,
    )
    assert unsign_payload(token, "wrong") is None
