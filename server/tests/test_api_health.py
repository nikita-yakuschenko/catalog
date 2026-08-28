from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.main import app


def test_health_ok():
    with patch("app.api.health.ping_database", new=AsyncMock(return_value=True)):
        with TestClient(app) as client:
            res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_health_database_unavailable():
    with patch("app.api.health.ping_database", new=AsyncMock(return_value=False)):
        with TestClient(app) as client:
            res = client.get("/health")
    assert res.status_code == 503
    assert res.json()["status"] == "unavailable"
