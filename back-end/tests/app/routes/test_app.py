from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routes.app import register
from shared.features import FeatureFlag, feature_flags


def create_app() -> FastAPI:
    app = FastAPI()
    register(app)
    return app


def test_get_backend_version(monkeypatch):
    app = create_app()
    monkeypatch.setattr("app.routes.app.get_version", lambda: "2026.10.02")

    response = TestClient(app).get("/api/app/version")

    assert response.status_code == 200
    assert response.json() == "2026.10.02"


def test_get_backend_features_only_exposes_dashboard_read_mode():
    flag = FeatureFlag.BACKEND_REDIS_DASHBOARD_ENABLED
    was_enabled = feature_flags.is_enabled(flag)
    try:
        for enabled in (False, True):
            feature_flags.set_enabled(flag, enabled)
            response = TestClient(create_app()).get("/api/app/features")
            assert response.status_code == 200
            assert response.json() == {
                "backendRedisDashboardEnabled": enabled,
            }
    finally:
        feature_flags.set_enabled(flag, was_enabled)
