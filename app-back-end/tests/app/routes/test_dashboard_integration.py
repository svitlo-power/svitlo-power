"""Integration tests for dashboard routes."""
import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from beanie import PydanticObjectId

from app.main import create_app
from app.settings import Settings
from shared.services.dashboard import ReadOnlyDashboardService
from shared.models.api.dashboard import (
    BuildingResponse,
    BuildingSummaryResponse,
    BuildingWithSummaryResponse,
    DashboardConfigResponse,
    PowerLogsResponse,
    PeriodResponse,
)


@pytest.fixture
def mock_settings():
    settings = MagicMock(spec=Settings)
    settings.DEBUG = True
    settings.APP_ACCESS_TOKEN = None
    return settings


@pytest.fixture
def mock_dashboard_service():
    return AsyncMock(spec=ReadOnlyDashboardService)


@pytest.fixture
def app(mock_settings, mock_dashboard_service):
    """Create test app with mocked dependencies."""
    from fastapi_injector import InjectorMiddleware, attach_injector
    from injector import Injector, Module, provider
    from app.container import AppModule
    
    # Create a test module that provides our mocked service
    class TestModule(Module):
        @provider
        def provide_dashboard_service(self) -> ReadOnlyDashboardService:
            return mock_dashboard_service
    
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