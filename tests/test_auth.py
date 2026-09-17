from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_healthz_without_token(monkeypatch):
    monkeypatch.setenv("API_TOKEN", "sekret")
    assert client.get("/healthz").status_code == 200


def test_homework_without_token(monkeypatch):
    monkeypatch.setenv("API_TOKEN", "sekret")
    r = client.get("/v1/homework?date=2026-09-15")
    assert r.status_code == 401
    assert r.json()["detail"] == "Invalid token"


def test_homework_with_wrong_token(monkeypatch):
    monkeypatch.setenv("API_TOKEN", "sekret")
    r = client.get(
        "/v1/homework?date=2026-09-15",
        headers={"Authorization": "Bearer wrong"},
    )
    assert r.status_code == 401
    assert r.json()["detail"] == "Invalid token"