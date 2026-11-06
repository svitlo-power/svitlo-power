from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from app.routes.app import register
from shared.features import FeatureFlag, feature_flags


def create_app() -> FastAPI:
    app = FastAPI()
    register(app)
    return app


@pytest.mark.parametrize("path", ["/api/app/version", "/api/version"])
def test_get_backend_version(monkeypatch, path):
    app = create_app()
    monkeypatch.setattr("app.routes.app.get_version", lambda: "2026.10.02")

    response = TestClient(app).get(path)

    assert response.status_code == 200
    assert response.json() == "2026.10.02"


def test_get_backend_features_only_exposes_dashboard_read_mode():
    flags = (
        FeatureFlag.DASHBOARD_UPDATED_EVENT,
        FeatureFlag.DASHBOARD_SNAPSHOT_PUBLISH,
        FeatureFlag.DEYE_POLLING_PROCESSING,
    )
    previous_values = {flag: feature_flags.is_enabled(flag) for flag in flags}
    try:
        combinations = (
            (False, True, False, False),
            (True, False, False, False),
            (True, True, True, False),
            (True, True, False, True),
        )
        for dashboard_enabled, publishing_enabled, deye_processing, expected in combinations:
            feature_flags.set_enabled(
                FeatureFlag.DASHBOARD_UPDATED_EVENT,
                dashboard_enabled,
            )
            feature_flags.set_enabled(
                FeatureFlag.DASHBOARD_SNAPSHOT_PUBLISH,
                publishing_enabled,
            )
            feature_flags.set_enabled(
                FeatureFlag.DEYE_POLLING_PROCESSING,
                deye_processing,
            )
            response = TestClient(create_app()).get("/api/app/features")
            assert response.status_code == 200
            assert response.json() == {
                "dashboardUpdatedEventEnabled": expected,
            }
    finally:
        for flag, enabled in previous_values.items():
            feature_flags.set_enabled(flag, enabled)
