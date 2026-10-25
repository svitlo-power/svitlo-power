from unittest.mock import AsyncMock, MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routes.settings import register
from app.utils.jwt_dependencies import jwt_required
from shared.models.system_setting import SystemSetting
from shared.services.settings.service import SettingsService


def make_read_only_setting():
    return SystemSetting(
        key="dashboard_outages_schedule_region",
        label="Schedule region",
        description="YASNO region ID",
        setting_type="number",
        default_value=0,
        value=25,
        editable=False,
        category_id="64a1a1a1a1a1a1a1a1a1a1a1",
    )


def make_test_client(settings_service):
    app = FastAPI()
    register(app)
    app.dependency_overrides[SettingsService] = lambda: settings_service
    app.dependency_overrides[jwt_required] = lambda: {"sub": "test-user"}
    return TestClient(app)


def test_single_setting_update_rejects_read_only_flag():
    settings_service = MagicMock()
    settings_service.get_setting = AsyncMock(return_value=make_read_only_setting())
    settings_service.set_value = AsyncMock()

    response = make_test_client(settings_service).put(
        "/api/settings/dashboard_outages_schedule_region",
        json={"value": 26},
    )

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "Setting 'dashboard_outages_schedule_region' is read-only"
    )
    settings_service.set_value.assert_not_awaited()


def test_bulk_setting_update_rejects_read_only_flag_before_updating():
    settings_service = MagicMock()
    settings_service.get_setting = AsyncMock(return_value=make_read_only_setting())
    settings_service.bulk_update = AsyncMock()

    response = make_test_client(settings_service).post(
        "/api/settings/bulk",
        json={"updates": {"dashboard_outages_schedule_region": 26}},
    )

    assert response.status_code == 409
    settings_service.bulk_update.assert_not_awaited()
