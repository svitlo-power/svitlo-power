from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routes.version import register


def test_get_backend_version(monkeypatch):
    app = FastAPI()
    register(app)
    monkeypatch.setattr("app.routes.version.get_version", lambda: "2026.10.02")

    response = TestClient(app).get("/api/version")

    assert response.status_code == 200
    assert response.json() == "2026.10.02"
