"""Integration tests for dashboard routes."""
import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from beanie import PydanticObjectId

from app.main import create_app
from app.settings import Settings
from shared.services.dashboard import ReadOnlyDashboardService
from shared.services.dashboard_snapshot import DashboardSnapshotClient
from shared.features import FeatureFlag, feature_flags
from shared.models.dashboard_snapshot import (
    BuildingSnapshot as DashboardBuildingSnapshot,
    ConfigSnapshot as DashboardConfigSnapshot,
    DashboardSnapshot,
)
from shared.models.api.dashboard import (
    BuildingResponse,
    BuildingSummaryResponse,
    BuildingWithSummaryResponse,
    DashboardConfigResponse,
    PowerLogsResponse,
    PeriodResponse,
)


@pytest.fixture(autouse=True)
def restore_snapshot_read_flag():
    original = feature_flags.is_enabled(
        FeatureFlag.APP_BACKEND_DASHBOARD_SNAPSHOT_READS
    )
    yield
    feature_flags.set_enabled(
        FeatureFlag.APP_BACKEND_DASHBOARD_SNAPSHOT_READS, original
    )


@pytest.fixture
def mock_settings():
    settings = MagicMock(spec=Settings)
    settings.DEBUG = True
    settings.APP_ACCESS_TOKEN = None
    settings.FEATURE_APP_BACKEND_DASHBOARD_SNAPSHOT_READS = False
    feature_flags.set_enabled(FeatureFlag.APP_BACKEND_DASHBOARD_SNAPSHOT_READS, False)
    return settings


@pytest.fixture
def mock_dashboard_service():
    return AsyncMock(spec=ReadOnlyDashboardService)


@pytest.fixture
def mock_snapshot_client():
    client = MagicMock(spec=DashboardSnapshotClient)
    client.get_snapshot.return_value = None
    client.is_stale = True
    client.get_outages_schedule.return_value = None
    return client


@pytest.fixture
def app(
    mock_settings,
    mock_dashboard_service,
    mock_snapshot_client,
):
    """Create test app with mocked dependencies."""
    from fastapi_injector import InjectorMiddleware, attach_injector
    from injector import Injector, Module, provider
    from app.container import AppModule
    
    # Create a test module that provides our mocked service
    class TestModule(Module):
        @provider
        def provide_dashboard_service(self) -> ReadOnlyDashboardService:
            return mock_dashboard_service

        @provider
        def provide_dashboard_snapshot_client(self) -> DashboardSnapshotClient:
            return mock_snapshot_client

    injector = Injector([AppModule(), TestModule()])
    app = create_app(mock_settings)
    app.add_middleware(InjectorMiddleware, injector=injector)
    attach_injector(app, injector)
    return app


@pytest.fixture
def client(app):
    return TestClient(app)


@pytest.fixture
def sample_building():
    building = MagicMock()
    building.id = PydanticObjectId()
    building.name = {"en": "Test Building"}
    building.color = "#FF0000"
    building.station = MagicMock()
    building.station.id = PydanticObjectId()
    building.station.station_name = "Test Station"
    building.station.battery_capacity = 10000
    building.station.connection_status = "ONLINE"
    building.report_users = []
    building.enabled = True
    building.order = 1
    return building


@pytest.fixture
def sample_dashboard_config():
    config = MagicMock()
    config.title = {"en": "Test Dashboard"}
    config.enable_outages_schedule = True
    config.outages_schedule_queue = "queue_1"
    return config


@pytest.fixture
def sample_ext_data():
    ext_data = MagicMock()
    ext_data.user_id = PydanticObjectId()
    ext_data.grid_state = True
    ext_data.received_at = datetime.now(timezone.utc)
    return ext_data


@pytest.fixture
def sample_station_data():
    station_data = MagicMock()
    station_data.station_id = 12345
    station_data.battery_soc = 85
    station_data.charge_power = -2000
    station_data.discharge_power = 0
    station_data.generation_power = 0
    station_data.wire_power = 0
    station_data.consumption_power = 1500
    station_data.last_update_time = datetime.now(timezone.utc)
    return station_data


class TestDashboardRoutes:
    @pytest.fixture
    def dashboard_snapshot(self):
        return DashboardSnapshot(
            epoch=1,
            version=2,
            generatedAt=datetime.now(timezone.utc),
            buildings=[
                DashboardBuildingSnapshot(
                    id="507f1f77bcf86cd799439011",
                    name={"en": "Cached Building", "uk": "Кешована будівля"},
                    color="#00FF00",
                    order=1,
                    hasBoundStation=True,
                    isGridAvailable=True,
                    batteryPercent=80,
                    isCharging=False,
                    isDischarging=True,
                    isOffline=False,
                    chargeSource="None",
                )
            ],
            config=DashboardConfigSnapshot(
                title={"en": "Cached Dashboard", "uk": "Кешована панель"},
                outagesSchedule={
                    "enable": True,
                    "regionId": 1,
                    "dsoId": 1,
                    "queue": "queue_1",
                },
            ),
            outagesSchedules={},
        )

    def test_redis_enabled_buildings_keeps_mobile_response_contract(
        self,
        client,
        app,
        mock_settings,
        mock_dashboard_service,
        mock_snapshot_client,
        dashboard_snapshot,
    ):
        mock_settings.FEATURE_APP_BACKEND_DASHBOARD_SNAPSHOT_READS = True
        feature_flags.set_enabled(FeatureFlag.APP_BACKEND_DASHBOARD_SNAPSHOT_READS, True)
        mock_snapshot_client.get_snapshot.return_value = dashboard_snapshot
        mock_snapshot_client.is_stale = False

        response = client.get("/api/dashboard/buildings")

        assert response.status_code == 200
        assert response.json() == [{
            "id": "507f1f77bcf86cd799439011",
            "name": {"en": "Cached Building", "uk": "Кешована будівля"},
            "color": "#00FF00",
            "hasBoundStation": True,
            "order": 1,
        }]
        mock_dashboard_service.get_buildings.assert_not_awaited()

    def test_redis_enabled_summary_keeps_requested_building_order(
        self,
        client,
        mock_settings,
        mock_dashboard_service,
        mock_snapshot_client,
        dashboard_snapshot,
    ):
        mock_settings.FEATURE_APP_BACKEND_DASHBOARD_SNAPSHOT_READS = True
        feature_flags.set_enabled(FeatureFlag.APP_BACKEND_DASHBOARD_SNAPSHOT_READS, True)
        mock_snapshot_client.get_snapshot.return_value = dashboard_snapshot
        mock_snapshot_client.is_stale = False

        response = client.post(
            "/api/dashboard/buildings/summary",
            json={"buildingIds": ["507f1f77bcf86cd799439011"]},
        )

        assert response.status_code == 200
        assert response.json()[0]["id"] == "507f1f77bcf86cd799439011"
        assert response.json()[0]["batteryPercent"] == 80
        mock_dashboard_service.get_buildings_summary.assert_not_awaited()

    def test_redis_enabled_combined_endpoint_keeps_mobile_response_contract(
        self,
        client,
        mock_settings,
        mock_dashboard_service,
        mock_snapshot_client,
        dashboard_snapshot,
    ):
        mock_settings.FEATURE_APP_BACKEND_DASHBOARD_SNAPSHOT_READS = True
        feature_flags.set_enabled(FeatureFlag.APP_BACKEND_DASHBOARD_SNAPSHOT_READS, True)
        mock_snapshot_client.get_snapshot.return_value = dashboard_snapshot
        mock_snapshot_client.is_stale = False

        response = client.get("/api/buildings/buildings")

        assert response.status_code == 200
        data = response.json()[0]
        assert data["id"] == "507f1f77bcf86cd799439011"
        assert data["name"]["en"] == "Cached Building"
        assert data["batteryPercent"] == 80
        assert data["chargeSource"] == "None"
        mock_dashboard_service.get_buildings_with_summary.assert_not_awaited()

    def test_redis_enabled_stale_snapshot_falls_back_to_legacy(
        self,
        client,
        mock_settings,
        mock_dashboard_service,
        mock_snapshot_client,
        dashboard_snapshot,
        sample_building,
    ):
        mock_settings.FEATURE_APP_BACKEND_DASHBOARD_SNAPSHOT_READS = True
        feature_flags.set_enabled(FeatureFlag.APP_BACKEND_DASHBOARD_SNAPSHOT_READS, True)
        mock_snapshot_client.get_snapshot.return_value = dashboard_snapshot
        mock_snapshot_client.is_stale = True
        mock_dashboard_service.get_buildings.return_value = [
            BuildingResponse(
                id=sample_building.id,
                name={"en": "Legacy Building"},
                color="#FF0000",
                hasBoundStation=True,
                order=1,
            )
        ]

        response = client.get("/api/dashboard/buildings")

        assert response.status_code == 200
        assert response.json()[0]["name"]["en"] == "Legacy Building"
        mock_dashboard_service.get_buildings.assert_awaited_once_with(all=False)

    def test_redis_enabled_config_keeps_flat_mobile_response(
        self,
        client,
        mock_settings,
        mock_dashboard_service,
        mock_snapshot_client,
        dashboard_snapshot,
    ):
        mock_settings.FEATURE_APP_BACKEND_DASHBOARD_SNAPSHOT_READS = True
        feature_flags.set_enabled(FeatureFlag.APP_BACKEND_DASHBOARD_SNAPSHOT_READS, True)
        mock_snapshot_client.get_snapshot.return_value = dashboard_snapshot
        mock_snapshot_client.is_stale = False

        response = client.get("/api/dashboard/config")

        assert response.status_code == 200
        assert response.json() == {
            "title": {"en": "Cached Dashboard", "uk": "Кешована панель"},
            "enableOutagesSchedule": True,
            "outagesScheduleQueue": "queue_1",
        }
        mock_dashboard_service.get_config.assert_not_awaited()

    def test_redis_dashboard_health_returns_consumer_state(
        self,
        client,
        mock_settings,
        mock_snapshot_client,
    ):
        mock_settings.FEATURE_APP_BACKEND_DASHBOARD_SNAPSHOT_READS = True
        feature_flags.set_enabled(FeatureFlag.APP_BACKEND_DASHBOARD_SNAPSHOT_READS, True)
        mock_snapshot_client.health.return_value = {
            "status": "healthy",
            "localEpoch": 1,
            "localVersion": 2,
            "redisEpoch": 1,
            "redisVersion": 2,
            "versionLag": 0,
            "snapshotAgeSeconds": 10,
            "isStale": False,
            "subscribed": True,
            "lastNotificationAt": None,
        }

        response = client.get("/health/redis-dashboard")

        assert response.status_code == 200
        assert response.json()["versionLag"] == 0

    def test_redis_dashboard_health_is_disabled_when_feature_is_off(
        self,
        client,
        mock_settings,
        mock_snapshot_client,
    ):
        mock_settings.FEATURE_APP_BACKEND_DASHBOARD_SNAPSHOT_READS = False
        feature_flags.set_enabled(FeatureFlag.APP_BACKEND_DASHBOARD_SNAPSHOT_READS, False)

        response = client.get("/health/redis-dashboard")

        assert response.status_code == 200
        assert response.json() == {"status": "disabled"}
        mock_snapshot_client.health.assert_not_called()

    def test_redis_dashboard_health_returns_503_when_unhealthy(
        self,
        client,
        mock_settings,
        mock_snapshot_client,
    ):
        mock_settings.FEATURE_APP_BACKEND_DASHBOARD_SNAPSHOT_READS = True
        feature_flags.set_enabled(FeatureFlag.APP_BACKEND_DASHBOARD_SNAPSHOT_READS, True)
        mock_snapshot_client.health.return_value = {"status": "unhealthy"}

        response = client.get("/health/redis-dashboard")

        assert response.status_code == 503

    @pytest.mark.asyncio
    async def test_get_buildings(self, client, mock_dashboard_service, sample_building):
        mock_dashboard_service.get_buildings.return_value = [
            BuildingResponse(
                id=sample_building.id,
                name={"en": "Test Building"},
                color="#FF0000",
                hasBoundStation=True,
                order=1
            )
        ]
        
        response = client.get("/api/dashboard/buildings")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"]["en"] == "Test Building"
        assert data[0]["color"] == "#FF0000"
        assert data[0]["hasBoundStation"] is True

    @pytest.mark.asyncio
    async def test_get_buildings_summary(self, client, mock_dashboard_service, sample_building, sample_ext_data, sample_station_data):
        mock_dashboard_service.get_buildings_summary.return_value = [
            BuildingSummaryResponse(
                id=sample_building.id,
                isGridAvailable=True,
                batteryPercent=85.0,
                isCharging=True,
                consumptionPower="1.5 kW",
                chargeSource="Grid"
            )
        ]
        
        response = client.post(
            "/api/dashboard/buildings/summary",
            json={"buildingIds": [str(sample_building.id)]}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["id"] == str(sample_building.id)
        assert data[0]["isGridAvailable"] is True
        assert data[0]["batteryPercent"] == 85.0

    @pytest.mark.asyncio
    async def test_get_buildings_with_summary(self, client, mock_dashboard_service, sample_building, sample_ext_data, sample_station_data):
        mock_dashboard_service.get_buildings_with_summary.return_value = [
            BuildingWithSummaryResponse(
                id=sample_building.id,
                name={"en": "Test Building"},
                color="#FF0000",
                hasBoundStation=True,
                order=1,
                isGridAvailable=True,
                batteryPercent=85.0,
                isCharging=True,
                consumptionPower="1.5 kW",
                chargeSource="Grid"
            )
        ]
        
        response = client.get("/api/buildings/buildings")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"]["en"] == "Test Building"
        assert data[0]["batteryPercent"] == 85.0

    @pytest.mark.asyncio
    async def test_get_dashboard_config(self, client, mock_dashboard_service, sample_dashboard_config):
        mock_dashboard_service.get_config.return_value = DashboardConfigResponse(
            title={"en": "Test Dashboard"},
            outagesSchedule={
                "enable": True,
                "region": "Kyiv",
                "dso": "Yasno",
                "queue": "queue_1",
            },
        )
        
        response = client.get("/api/dashboard/config")
        
        assert response.status_code == 200
        data = response.json()
        assert data["title"]["en"] == "Test Dashboard"
        assert "outagesSchedule" not in data
        assert data["enableOutagesSchedule"] is True
        assert data["outagesScheduleQueue"] == "queue_1"

    @pytest.mark.asyncio
    async def test_get_dashboard_config_alias(self, client, mock_dashboard_service, sample_dashboard_config):
        mock_dashboard_service.get_config.return_value = DashboardConfigResponse(
            title={"en": "Test Dashboard"},
            outagesSchedule={
                "enable": True,
                "region": "Kyiv",
                "dso": "Yasno",
                "queue": "queue_1",
            },
        )
        
        response = client.get("/api/buildings/dashboardConfig")
        
        assert response.status_code == 200
        data = response.json()
        assert data["title"]["en"] == "Test Dashboard"
        assert "outagesSchedule" not in data
        assert data["enableOutagesSchedule"] is True
        assert data["outagesScheduleQueue"] == "queue_1"

    @pytest.mark.asyncio
    async def test_get_dashboard_config_legacy_fields_when_schedule_disabled(
        self, client, mock_dashboard_service,
    ):
        mock_dashboard_service.get_config.return_value = DashboardConfigResponse(
            title={"en": "Test Dashboard"},
            outagesSchedule=None,
        )

        response = client.get("/api/dashboard/config")

        assert response.status_code == 200
        assert "outagesSchedule" not in response.json()
        assert response.json()["enableOutagesSchedule"] is False
        assert response.json()["outagesScheduleQueue"] is None

    @pytest.mark.asyncio
    async def test_get_building_power_logs_success(self, client, mock_dashboard_service):
        building_id = PydanticObjectId()
        mock_dashboard_service.get_power_logs.return_value = PowerLogsResponse(
            periods=[
                PeriodResponse(
                    startTime="2024-01-15T00:00:00Z",
                    endTime="2024-01-15T01:00:00Z",
                    isAvailable=True,
                    durationSeconds=3600
                )
            ],
            totalAvailableSeconds=3600,
            totalUnavailableSeconds=0,
            totalGeneratorSeconds=0,
            totalSeconds=3600
        )
        
        response = client.post(
            f"/api/dashboard/buildings/{building_id}/power-logs",
            json={"startDate": "2024-01-15T00:00:00Z", "endDate": "2024-01-15T01:00:00Z"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["periods"]) == 1
        assert data["totalAvailableSeconds"] == 3600

    @pytest.mark.asyncio
    async def test_get_building_power_logs_invalid_date(self, client, mock_dashboard_service):
        building_id = PydanticObjectId()
        
        response = client.post(
            f"/api/dashboard/buildings/{building_id}/power-logs",
            json={"startDate": "invalid", "endDate": "2024-01-15T01:00:00Z"}
        )
        
        assert response.status_code == 400
        assert "Invalid date format" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_building_power_logs_start_after_end(self, client, mock_dashboard_service):
        building_id = PydanticObjectId()
        
        response = client.post(
            f"/api/dashboard/buildings/{building_id}/power-logs",
            json={"startDate": "2024-01-15T01:00:00Z", "endDate": "2024-01-15T00:00:00Z"}
        )
        
        assert response.status_code == 400
        assert "startDate must be before endDate" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_building_power_logs_not_found(self, client, mock_dashboard_service):
        building_id = PydanticObjectId()
        mock_dashboard_service.get_power_logs.return_value = None
        
        response = client.post(
            f"/api/dashboard/buildings/{building_id}/power-logs",
            json={"startDate": "2024-01-15T00:00:00Z", "endDate": "2024-01-15T01:00:00Z"}
        )
        
        assert response.status_code == 404
        assert "Building not found or no power logs available" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_building_power_logs_alias(self, client, mock_dashboard_service):
        building_id = PydanticObjectId()
        mock_dashboard_service.get_power_logs.return_value = PowerLogsResponse(
            periods=[
                PeriodResponse(
                    startTime="2024-01-15T00:00:00Z",
                    endTime="2024-01-15T01:00:00Z",
                    isAvailable=True,
                    durationSeconds=3600
                )
            ],
            totalAvailableSeconds=3600,
            totalUnavailableSeconds=0,
            totalGeneratorSeconds=0,
            totalSeconds=3600
        )
        
        response = client.post(
            f"/api/buildings/{building_id}/power-logs",
            json={"startDate": "2024-01-15T00:00:00Z", "endDate": "2024-01-15T01:00:00Z"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert len(data["periods"]) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])