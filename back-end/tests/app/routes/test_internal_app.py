import asyncio
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from beanie import PydanticObjectId
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routes.internal_app import register
from app.services import PushService
from shared.models.api.dashboard import (
    BuildingResponse, BuildingSummaryResponse, BuildingWithSummaryResponse,
    DashboardConfigResponse, PowerLogsResponse,
)
from shared.models.api.push import PushDeviceResponse, PushTopicResponse
from shared.models.localizable_value import LocalizableValue
from shared.models.outages_schedule import SchedulesResponse
from shared.health import HealthCheckResult, HealthStatus, health_registry
from shared.services import OutagesScheduleService
from shared.services.dashboard import ReadOnlyDashboardService


CONTRACT_PATH = Path(__file__).resolve().parents[3] / "contracts" / "internal-app-api.v1.openapi.json"


def client(token="test-token", services=None, timeout=1):
    app = FastAPI()
    app.state.settings = SimpleNamespace(
        INTERNAL_API_TOKEN=token, INTERNAL_API_TIMEOUT_SECONDS=timeout
    )
    app.state.injector = MagicMock()
    app.state.injector.get.side_effect = lambda cls: services[cls]
    register(app)
    return TestClient(app)


def test_internal_api_requires_valid_service_token():
    api = client()
    assert api.get("/internal/v1/app/health").status_code == 401
    assert api.get("/internal/v1/app/health", headers={"Authorization": "Bearer wrong"}).status_code == 401
    response = api.get("/internal/v1/app/health", headers={"Authorization": "Bearer test-token"})
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_internal_api_is_disabled_without_token():
    assert client(None).get("/internal/v1/app/health").status_code == 503


@pytest.fixture
def services():
    return {
        ReadOnlyDashboardService: MagicMock(),
        OutagesScheduleService: MagicMock(),
        PushService: MagicMock(),
    }


@pytest.fixture
def api(services):
    result = client(services=services)
    result.headers.update({"Authorization": "Bearer test-token"})
    return result


@pytest.mark.parametrize("method,path", [
    ("GET", "/dashboard/buildings"),
    ("POST", "/dashboard/buildings/summary"),
    ("GET", "/dashboard/buildings-with-summary"),
    ("GET", "/dashboard/config"),
    ("POST", "/dashboard/buildings/507f1f77bcf86cd799439011/power-logs"),
    ("GET", "/outages-schedule/1.1"),
    ("POST", "/push/devices"),
    ("POST", "/push/devices/current"),
    ("POST", "/push/devices/subscriptions"),
    ("POST", "/push/devices/unregister"),
    ("GET", "/push/topics"),
])
def test_all_domain_routes_require_authentication(method, path, services):
    api = client(services=services)
    assert api.request(method, "/internal/v1/app" + path, json={}).status_code == 401
    api.app.state.injector.get.assert_not_called()


def test_dashboard_contract(api, services):
    dashboard = services[ReadOnlyDashboardService]
    building_id = PydanticObjectId("507f1f77bcf86cd799439011")
    building = BuildingResponse(id=building_id, name=LocalizableValue({"en": "Home"}), color="#ffffff", order=1)
    summary = BuildingSummaryResponse(id=building_id, is_grid_available=True)
    combined = BuildingWithSummaryResponse(**building.model_dump(), is_grid_available=True)
    dashboard.get_buildings = AsyncMock(return_value=[building])
    dashboard.get_buildings_summary = AsyncMock(return_value=[summary])
    dashboard.get_buildings_with_summary = AsyncMock(return_value=[combined])
    dashboard.get_config = AsyncMock(return_value=DashboardConfigResponse(title=LocalizableValue({"en": "Home"})))
    dashboard.get_power_logs = AsyncMock(return_value=PowerLogsResponse(
        periods=[], total_available_seconds=0, total_unavailable_seconds=0, total_seconds=0
    ))

    response = api.get("/internal/v1/app/dashboard/buildings")
    assert response.status_code == 200
    assert response.json()[0]["id"] == str(building_id)
    assert response.json()[0]["hasBoundStation"] is False
    dashboard.get_buildings.assert_awaited_once_with(all=False)
    response = api.post("/internal/v1/app/dashboard/buildings/summary", json={"buildingIds": [str(building_id)]})
    assert response.status_code == 200
    assert response.json()[0]["isGridAvailable"] is True
    assert api.get("/internal/v1/app/dashboard/buildings-with-summary").json()[0]["name"] == {"en": "Home"}
    assert api.get("/internal/v1/app/dashboard/config").json()["title"] == {"en": "Home"}
    response = api.post(f"/internal/v1/app/dashboard/buildings/{building_id}/power-logs", json={
        "startDate": "2026-01-01T00:00:00Z", "endDate": "2026-01-02T00:00:00Z"
    })
    assert response.status_code == 200
    assert response.json()["totalSeconds"] == 0
    dashboard.get_power_logs.assert_awaited_once_with(
        building_id, datetime(2026, 1, 1, tzinfo=timezone.utc), datetime(2026, 1, 2, tzinfo=timezone.utc)
    )


def test_schedule_contract_and_missing_queue(api, services):
    schedule = services[OutagesScheduleService]
    schedule.get_schedule_async = AsyncMock(return_value=SchedulesResponse.model_validate({
        "1.1": {"days": [], "updatedOn": "2026-01-01T00:00:00Z"}
    }))
    response = api.get("/internal/v1/app/outages-schedule/1.1")
    assert response.status_code == 200
    assert response.json()["days"] == []
    assert "updatedOn" in response.json()
    assert api.get("/internal/v1/app/outages-schedule/1.2").status_code == 404


def test_push_contract(api, services):
    push = services[PushService]
    now = datetime.now(timezone.utc)
    device = PushDeviceResponse(
        id=PydanticObjectId(), platform="android", language="uk", enabled=True,
        disabled_topics=[], buildings=[], created_at=now, last_seen=now,
    )
    push.register_device = AsyncMock(return_value=device)
    push.get_device = AsyncMock(return_value=device)
    push.update_subscriptions = AsyncMock(return_value=device)
    push.unregister_device = AsyncMock(return_value=False)
    push.get_enabled_topics = AsyncMock(return_value=[PushTopicResponse(key="news", name={"en": "News"}, description={})])
    base = "/internal/v1/app/push"
    response = api.post(base + "/devices", json={"token": "device-secret", "platform": "android"})
    assert response.status_code == 200
    assert "device-secret" not in response.text
    assert "lastSeen" in response.json()
    assert api.post(base + "/devices/current", json={"token": "device-secret"}).status_code == 200
    assert api.post(base + "/devices/subscriptions", json={"token": "device-secret"}).status_code == 200
    assert api.post(base + "/devices/unregister", json={"token": "device-secret"}).json() == {"success": True}
    assert api.get(base + "/topics").json()[0]["key"] == "news"
    push.get_device.return_value = None
    push.update_subscriptions.return_value = None
    assert api.post(base + "/devices/current", json={"token": "missing"}).status_code == 404
    assert api.post(base + "/devices/subscriptions", json={"token": "missing"}).status_code == 404


def test_validation_and_missing_power_logs(api, services):
    dashboard = services[ReadOnlyDashboardService]
    dashboard.get_power_logs = AsyncMock(return_value=None)
    base = "/internal/v1/app/dashboard/buildings/507f1f77bcf86cd799439011/power-logs"
    assert api.post("/internal/v1/app/dashboard/buildings/summary", json={"buildingIds": ["bad"]}).status_code == 422
    assert api.post("/internal/v1/app/push/devices", json={"token": "", "platform": "ios"}).status_code == 422
    assert api.post(base, json={"startDate": "bad", "endDate": "bad"}).status_code == 400
    assert api.post(base, json={"startDate": "2026-01-02", "endDate": "2026-01-01"}).status_code == 400
    assert api.post(base, json={"startDate": "2026-01-01", "endDate": "2026-01-02"}).status_code == 404
    dashboard.get_power_logs.assert_awaited_once()


def test_dependency_failure_and_timeout(services):
    dashboard = services[ReadOnlyDashboardService]
    dashboard.get_buildings = AsyncMock(side_effect=RuntimeError("private detail"))
    api = client(services=services, timeout=0.01)
    api.headers.update({"Authorization": "Bearer test-token"})
    response = api.get("/internal/v1/app/dashboard/buildings")
    assert response.status_code == 503
    assert response.json() == {"detail": "Dependency unavailable"}
    async def stalled(**kwargs):
        await asyncio.Event().wait()
    dashboard.get_buildings = AsyncMock(side_effect=stalled)
    response = api.get("/internal/v1/app/dashboard/buildings")
    assert response.status_code == 504
    assert response.json() == {"detail": "Dependency timed out"}


def test_readiness_reports_critical_dependencies(api, monkeypatch):
    checks = {
        "mongodb": AsyncMock(return_value=HealthCheckResult(HealthStatus.HEALTHY, "mongodb")),
        "redis": AsyncMock(return_value=HealthCheckResult(HealthStatus.HEALTHY, "redis")),
    }
    monkeypatch.setattr(health_registry, "_checks", checks)
    response = api.get("/internal/v1/app/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready", "checks": {"mongodb": "healthy", "redis": "healthy"}}

    checks["redis"].return_value = HealthCheckResult(HealthStatus.UNHEALTHY, "redis", message="secret host")
    response = api.get("/internal/v1/app/ready")
    assert response.status_code == 503
    assert response.json() == {"status": "not_ready", "checks": {"mongodb": "healthy", "redis": "unhealthy"}}
    assert "secret host" not in response.text


def test_readiness_requires_authentication(services):
    assert client(services=services).get("/internal/v1/app/ready").status_code == 401


def internal_openapi_contract(app: FastAPI) -> dict:
    """Internal paths plus every component schema they reference, in a stable form."""
    schema = app.openapi()
    paths = {path: item for path, item in schema["paths"].items() if path.startswith("/internal/v1/app")}
    components = schema.get("components", {}).get("schemas", {})
    referenced, pending = set(), [paths]
    while pending:
        node = pending.pop()
        if isinstance(node, dict):
            ref = node.get("$ref")
            if isinstance(ref, str) and ref.startswith("#/components/schemas/"):
                name = ref.rsplit("/", 1)[1]
                if name not in referenced:
                    referenced.add(name)
                    pending.append(components[name])
            pending.extend(node.values())
        elif isinstance(node, list):
            pending.extend(node)
    return {
        "openapi": schema["openapi"],
        "paths": paths,
        "components": {"schemas": {name: components[name] for name in sorted(referenced)}},
    }


def test_openapi_contract_matches_snapshot(services):
    """Fails when the wire contract changes; regenerate with UPDATE_INTERNAL_API_CONTRACT=1."""
    actual = json.dumps(internal_openapi_contract(client(services=services).app), indent=2, sort_keys=True) + "\n"
    if os.environ.get("UPDATE_INTERNAL_API_CONTRACT") == "1":
        CONTRACT_PATH.write_text(actual, encoding="utf-8", newline="\n")
    assert CONTRACT_PATH.exists(), f"Missing {CONTRACT_PATH}; run with UPDATE_INTERNAL_API_CONTRACT=1"
    assert json.loads(actual) == json.loads(CONTRACT_PATH.read_text(encoding="utf-8")), (
        "Internal app API contract changed. If intentional, regenerate with UPDATE_INTERNAL_API_CONTRACT=1 "
        "and coordinate the change with the app BFF consumer."
    )


def test_real_registration_and_service_bindings(mock_settings, monkeypatch):
    from aiohttp import ClientSession
    from app.app_container import init_container
    from app.routes import register_routes
    from app.services import DashboardService
    from shared.services.translation.service import TranslationService

    # init_container and register_routes mutate process-wide state; keep it local to this test.
    monkeypatch.setattr(TranslationService, "i18n", {})
    monkeypatch.setattr(health_registry, "_checks", {})

    mock_settings.INTERNAL_API_TOKEN = "test-token"
    mock_settings.INTERNAL_API_TIMEOUT_SECONDS = 1
    mock_settings.FIREBASE_CREDENTIALS = None
    app = FastAPI()
    app.state.settings = mock_settings
    injector = init_container(app, mock_settings)
    app.state.injector = injector
    injector.binder.bind(ClientSession, to=MagicMock(spec=ClientSession))
    register_routes(app)
    assert isinstance(injector.get(ReadOnlyDashboardService), DashboardService)
    assert isinstance(injector.get(OutagesScheduleService), OutagesScheduleService)
    assert isinstance(injector.get(PushService), PushService)
    response = TestClient(app).get(
        "/internal/v1/app/health", headers={"Authorization": "Bearer test-token"}
    )
    assert response.status_code == 200