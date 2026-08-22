"""Tests for app/routes/dashboard.py."""
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routes.dashboard import register
from app.utils.jwt_dependencies import jwt_required, get_current_jwt_optional
from shared.models.localizable_value import LocalizableValue


class TestDashboardRoute:
    def test_register_adds_routes(self):
        app = FastAPI()
        register(app)
        routes = [r.path for r in app.routes]
        assert "/api/dashboard/buildings" in routes
        assert "/api/dashboard/buildings/summary" in routes
        assert "/api/buildings/buildings" in routes
        assert "/api/dashboard/config" in routes
        assert "/api/buildings/dashboardConfig" in routes
        assert "/api/dashboard/buildings/{building_id}" in routes
        assert "/api/dashboard/buildings" in routes

    def test_get_buildings_exists(self):
        app = FastAPI()
        register(app)

        mock_injector = MagicMock()
        mock_dashboard = MagicMock()
        mock_dashboard.get_buildings = AsyncMock(return_value=[])
        mock_settings = MagicMock()
        mock_settings.JWT_SECRET_KEY = "test-key"
        mock_injector.get = MagicMock(side_effect=lambda cls: mock_dashboard if cls.__name__ == "DashboardService" else mock_settings)
        app.state.injector = mock_injector

        client = TestClient(app)
        response = client.get("/api/dashboard/buildings")
        # Should not return 404 (route exists)
        assert response.status_code != 404

    def test_get_dashboard_config_exists(self):
        app = FastAPI()
        register(app)

        mock_injector = MagicMock()
        mock_dashboard = MagicMock()
        # Create a proper mock response that matches DashboardConfigResponse
        from app.models.api.dashboard import DashboardConfigResponse
        mock_config = DashboardConfigResponse(
            title=LocalizableValue({"en": "Test Title", "uk": "Тестовий заголовок"}),
            enable_outages_schedule=True,
            outages_schedule_queue="test-queue"
        )
        mock_dashboard.get_config = AsyncMock(return_value=mock_config)
        mock_settings = MagicMock()
        mock_settings.JWT_SECRET_KEY = "test-key"
        mock_injector.get = MagicMock(side_effect=lambda cls: mock_dashboard if cls.__name__ == "DashboardService" else mock_settings)
        app.state.injector = mock_injector

        client = TestClient(app)
        response = client.get("/api/dashboard/config")
        # Should not return 404 (route exists)
        assert response.status_code != 404

    def test_get_buildings_with_jwt(self):
        """Test get_buildings with valid JWT returns buildings."""
        app = FastAPI()
        register(app)

        mock_building = MagicMock()
        mock_building.id = "507f1f77bcf86cd799439011"
        mock_building.name = LocalizableValue({"en": "Building 1"})
        mock_building.color = "#FF0000"
        mock_building.has_bound_station = False
        mock_building.order = 1

        mock_dashboard = MagicMock()
        mock_dashboard.get_buildings = AsyncMock(return_value=[mock_building])

        mock_injector = MagicMock()
        mock_injector.get = MagicMock(return_value=mock_dashboard)
        app.state.injector = mock_injector

        app.dependency_overrides[get_current_jwt_optional] = lambda: {"sub": "testuser"}

        client = TestClient(app)
        response = client.get("/api/dashboard/buildings")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1

        app.dependency_overrides.clear()

    def test_get_buildings_without_jwt(self):
        """Test get_buildings without JWT returns buildings with all=False."""
        app = FastAPI()
        register(app)

        mock_building = MagicMock()
        mock_building.id = "507f1f77bcf86cd799439011"
        mock_building.name = LocalizableValue({"en": "Building 1"})
        mock_building.color = "#FF0000"
        mock_building.has_bound_station = False
        mock_building.order = 1

        mock_dashboard = MagicMock()
        mock_dashboard.get_buildings = AsyncMock(return_value=[mock_building])

        mock_injector = MagicMock()
        mock_injector.get = MagicMock(return_value=mock_dashboard)
        app.state.injector = mock_injector

        app.dependency_overrides[get_current_jwt_optional] = lambda: None

        client = TestClient(app)
        response = client.get("/api/dashboard/buildings")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1

        app.dependency_overrides.clear()

    def test_get_buildings_summary(self):
        """Test get_buildings_summary returns summary."""
        app = FastAPI()
        register(app)

        from app.models.api.dashboard import BuildingSummaryResponse
        from beanie import PydanticObjectId
        mock_summary = BuildingSummaryResponse(
            id=PydanticObjectId("507f1f77bcf86cd799439011"),
        )

        mock_dashboard = MagicMock()
        mock_dashboard.get_buildings_summary = AsyncMock(return_value=[mock_summary])

        mock_injector = MagicMock()
        mock_injector.get = MagicMock(return_value=mock_dashboard)
        app.state.injector = mock_injector

        client = TestClient(app)
        response = client.post("/api/dashboard/buildings/summary", json={
            "buildingIds": ["507f1f77bcf86cd799439011"],
        })
        assert response.status_code == 200

    def test_get_buildings_data(self):
        """Test get_buildings_data returns buildings with summary."""
        app = FastAPI()
        register(app)

        from app.models.api.dashboard import BuildingWithSummaryResponse
        from beanie import PydanticObjectId
        mock_building = BuildingWithSummaryResponse(
            id=PydanticObjectId("507f1f77bcf86cd799439011"),
            name=LocalizableValue({"en": "Building 1"}),
            color="#FF0000",
            has_bound_station=False,
            order=1,
        )

        mock_dashboard = MagicMock()
        mock_dashboard.get_buildings_with_summary = AsyncMock(return_value=[mock_building])

        mock_injector = MagicMock()
        mock_injector.get = MagicMock(return_value=mock_dashboard)
        app.state.injector = mock_injector

        client = TestClient(app)
        response = client.get("/api/buildings/buildings")
        assert response.status_code == 200

    def test_get_dashboard_config_success(self):
        """Test get_dashboard_config returns config."""
        app = FastAPI()
        register(app)

        from app.models.api.dashboard import DashboardConfigResponse
        mock_config = DashboardConfigResponse(
            title=LocalizableValue({"en": "Test Title"}),
            enable_outages_schedule=True,
            outages_schedule_queue="test-queue"
        )

        mock_dashboard = MagicMock()
        mock_dashboard.get_config = AsyncMock(return_value=mock_config)

        mock_injector = MagicMock()
        mock_injector.get = MagicMock(return_value=mock_dashboard)
        app.state.injector = mock_injector

        client = TestClient(app)
        response = client.get("/api/dashboard/config")
        assert response.status_code == 200
        data = response.json()
        assert data["enableOutagesSchedule"] is True

    def test_update_dashboard_config(self):
        """Test update_dashboard_config saves config."""
        app = FastAPI()
        register(app)

        from app.models.api.dashboard import DashboardConfigResponse
        mock_config = DashboardConfigResponse(
            title=LocalizableValue({"en": "Test Title"}),
            enable_outages_schedule=True,
            outages_schedule_queue="test-queue"
        )

        mock_dashboard = MagicMock()
        mock_dashboard.save_config = AsyncMock(return_value=mock_config)

        mock_injector = MagicMock()
        mock_injector.get = MagicMock(return_value=mock_dashboard)
        app.state.injector = mock_injector

        app.dependency_overrides[jwt_required] = lambda: {"sub": "testuser"}

        client = TestClient(app)
        response = client.put("/api/dashboard/config", json={
            "title": {"en": "Test Title"},
            "enableOutagesSchedule": True,
            "outagesScheduleQueue": "test-queue",
        })
        assert response.status_code == 200

        app.dependency_overrides.clear()

    def test_get_building_success(self):
        """Test get_building returns building."""
        app = FastAPI()
        register(app)

        from app.models.api.dashboard import EditBuildingResponse
        from beanie import PydanticObjectId
        mock_building = EditBuildingResponse(
            id=PydanticObjectId("507f1f77bcf86cd799439011"),
            name=LocalizableValue({"en": "Building 1"}),
            color="#FF0000",
            has_bound_station=False,
            order=1,
            report_user_ids=[],
            station_id=None,
            enabled=True,
        )

        mock_dashboard = MagicMock()
        mock_dashboard.get_building = AsyncMock(return_value=mock_building)

        mock_injector = MagicMock()
        mock_injector.get = MagicMock(return_value=mock_dashboard)
        app.state.injector = mock_injector

        app.dependency_overrides[jwt_required] = lambda: {"sub": "testuser"}

        client = TestClient(app)
        response = client.get("/api/dashboard/buildings/507f1f77bcf86cd799439011")
        assert response.status_code == 200

        app.dependency_overrides.clear()

    def test_get_building_not_found(self):
        """Test get_building returns 404 when building not found."""
        app = FastAPI()
        register(app)

        mock_dashboard = MagicMock()
        mock_dashboard.get_building = AsyncMock(return_value=None)

        mock_injector = MagicMock()
        mock_injector.get = MagicMock(return_value=mock_dashboard)
        app.state.injector = mock_injector

        app.dependency_overrides[jwt_required] = lambda: {"sub": "testuser"}

        client = TestClient(app)
        response = client.get("/api/dashboard/buildings/507f1f77bcf86cd799439011")
        assert response.status_code == 404
        assert "Building not found" in response.json()["detail"]

        app.dependency_overrides.clear()

    def test_edit_building(self):
        """Test edit_building updates building."""
        app = FastAPI()
        register(app)

        mock_dashboard = MagicMock()
        mock_dashboard.edit_building = AsyncMock()

        mock_injector = MagicMock()
        mock_injector.get = MagicMock(return_value=mock_dashboard)
        app.state.injector = mock_injector

        app.dependency_overrides[jwt_required] = lambda: {"sub": "testuser"}

        client = TestClient(app)
        response = client.put("/api/dashboard/buildings/507f1f77bcf86cd799439011", json={
            "name": {"en": "Building 1"},
            "color": "#FF0000",
            "stationId": None,
            "reportUserIds": [],
            "enabled": True,
            "order": 1,
        })
        assert response.status_code == 200
        assert response.json()["success"] is True

        app.dependency_overrides.clear()

    def test_create_building(self):
        """Test create_building creates a new building."""
        app = FastAPI()
        register(app)

        mock_dashboard = MagicMock()
        mock_dashboard.create_building = AsyncMock(return_value="507f1f77bcf86cd799439011")

        mock_injector = MagicMock()
        mock_injector.get = MagicMock(return_value=mock_dashboard)
        app.state.injector = mock_injector

        app.dependency_overrides[jwt_required] = lambda: {"sub": "testuser"}

        client = TestClient(app)
        response = client.post("/api/dashboard/buildings", json={
            "name": {"en": "New Building"},
            "color": "#FF0000",
            "stationId": None,
            "reportUserIds": [],
            "enabled": True,
            "order": 1,
        })
        assert response.status_code == 200
        assert response.json()["success"] is True

        app.dependency_overrides.clear()

    def test_delete_building(self):
        """Test delete_building deletes a building."""
        app = FastAPI()
        register(app)

        mock_dashboard = MagicMock()
        mock_dashboard.delete_building = AsyncMock(return_value=True)

        mock_injector = MagicMock()
        mock_injector.get = MagicMock(return_value=mock_dashboard)
        app.state.injector = mock_injector

        app.dependency_overrides[jwt_required] = lambda: {"sub": "testuser"}

        client = TestClient(app)
        response = client.delete("/api/dashboard/buildings/507f1f77bcf86cd799439011")
        assert response.status_code == 200
        assert response.json()["success"] is True

        app.dependency_overrides.clear()

    def test_get_building_power_logs_success(self):
        """Test get_building_power_logs returns power logs."""
        app = FastAPI()
        register(app)

        mock_power_logs = MagicMock()
        mock_power_logs.model_dump.return_value = {"periods": []}

        mock_dashboard = MagicMock()
        mock_dashboard.get_power_logs = AsyncMock(return_value=mock_power_logs)

        mock_injector = MagicMock()
        mock_injector.get = MagicMock(return_value=mock_dashboard)
        app.state.injector = mock_injector

        client = TestClient(app)
        response = client.post("/api/dashboard/buildings/507f1f77bcf86cd799439011/power-logs", json={
            "startDate": "2024-01-01T00:00:00Z",
            "endDate": "2024-01-02T00:00:00Z",
        })
        assert response.status_code == 200

    def test_get_building_power_logs_invalid_dates(self):
        """Test get_building_power_logs returns 400 for invalid dates."""
        app = FastAPI()
        register(app)

        mock_dashboard = MagicMock()
        mock_dashboard.get_power_logs = AsyncMock()

        mock_injector = MagicMock()
        mock_injector.get = MagicMock(return_value=mock_dashboard)
        app.state.injector = mock_injector

        client = TestClient(app)
        response = client.post("/api/dashboard/buildings/507f1f77bcf86cd799439011/power-logs", json={
            "startDate": "invalid-date",
            "endDate": "2024-01-02T00:00:00Z",
        })
        assert response.status_code == 400
        assert "Invalid date format" in response.json()["detail"]

    def test_get_building_power_logs_start_after_end(self):
        """Test get_building_power_logs returns 400 when start >= end."""
        app = FastAPI()
        register(app)

        mock_dashboard = MagicMock()
        mock_dashboard.get_power_logs = AsyncMock()

        mock_injector = MagicMock()
        mock_injector.get = MagicMock(return_value=mock_dashboard)
        app.state.injector = mock_injector

        client = TestClient(app)
        response = client.post("/api/dashboard/buildings/507f1f77bcf86cd799439011/power-logs", json={
            "startDate": "2024-01-02T00:00:00Z",
            "endDate": "2024-01-01T00:00:00Z",
        })
        assert response.status_code == 400
        assert "startDate must be before endDate" in response.json()["detail"]

    def test_get_building_power_logs_not_found(self):
        """Test get_building_power_logs returns 404 when no power logs."""
        app = FastAPI()
        register(app)

        mock_dashboard = MagicMock()
        mock_dashboard.get_power_logs = AsyncMock(return_value=None)

        mock_injector = MagicMock()
        mock_injector.get = MagicMock(return_value=mock_dashboard)
        app.state.injector = mock_injector

        client = TestClient(app)
        response = client.post("/api/dashboard/buildings/507f1f77bcf86cd799439011/power-logs", json={
            "startDate": "2024-01-01T00:00:00Z",
            "endDate": "2024-01-02T00:00:00Z",
        })
        assert response.status_code == 404
        assert "Building not found" in response.json()["detail"]
