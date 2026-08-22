"""Tests for app/routes/station_connections.py."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routes.station_connections import register
from app.utils.jwt_dependencies import jwt_required


class TestStationConnectionsRoute:
    def test_register_adds_routes(self):
        app = FastAPI()
        register(app)
        routes = [r.path for r in app.routes]
        assert "/api/station-connections" in routes
        assert "/api/station-connections/defaults" in routes

    def test_get_connections_requires_jwt(self):
        app = FastAPI()
        register(app)

        client = TestClient(app)
        response = client.get("/api/station-connections")
        assert response.status_code == 401

    def test_get_connection_defaults_requires_jwt(self):
        app = FastAPI()
        register(app)

        client = TestClient(app)
        response = client.get("/api/station-connections/defaults")
        assert response.status_code == 401

    def test_get_connections_success(self):
        """Test get_connections returns connections."""
        app = FastAPI()
        register(app)

        from app.models.api import StationConnectionResponse
        from beanie import PydanticObjectId
        mock_connection = StationConnectionResponse(
            id=PydanticObjectId("507f1f77bcf86cd799439011"),
            name="Test Connection",
            base_url="https://api.example.com",
            app_id="app123",
            email="test@example.com",
            sync_stations_on_poll=False,
        )

        mock_service = MagicMock()
        mock_service.get_connections = MagicMock(return_value=[mock_connection])

        mock_injector = MagicMock()
        mock_injector.get = MagicMock(return_value=mock_service)
        app.state.injector = mock_injector

        app.dependency_overrides[jwt_required] = lambda: {"sub": "testuser"}

        client = TestClient(app)
        response = client.get("/api/station-connections")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "Test Connection"

        app.dependency_overrides.clear()

    def test_get_connection_defaults_success(self):
        """Test get_connection_defaults returns defaults."""
        app = FastAPI()
        register(app)

        mock_settings = MagicMock()
        mock_settings.DEYE_BASE_URL = "https://api.example.com"

        mock_injector = MagicMock()
        mock_injector.get = MagicMock(return_value=mock_settings)
        app.state.injector = mock_injector

        app.dependency_overrides[jwt_required] = lambda: {"sub": "testuser"}

        client = TestClient(app)
        response = client.get("/api/station-connections/defaults")
        assert response.status_code == 200
        data = response.json()
        assert data["baseUrl"] == "https://api.example.com"

        app.dependency_overrides.clear()

    def test_create_connection_success(self):
        """Test create_connection creates a new connection."""
        app = FastAPI()
        register(app)

        mock_connection = MagicMock()
        mock_connection.id = "507f1f77bcf86cd799439011"

        mock_service = MagicMock()
        mock_service.create_connection = AsyncMock(return_value=mock_connection)

        mock_injector = MagicMock()
        mock_injector.get = MagicMock(return_value=mock_service)
        app.state.injector = mock_injector

        app.dependency_overrides[jwt_required] = lambda: {"sub": "testuser"}

        client = TestClient(app)
        response = client.post("/api/station-connections", json={
            "name": "Test Connection",
            "baseUrl": "https://api.example.com",
            "appId": "app123",
            "appSecret": "secret123",
            "email": "test@example.com",
            "password": "password123",
            "syncStationsOnPoll": False,
        })
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["id"] == "507f1f77bcf86cd799439011"

        app.dependency_overrides.clear()

    def test_update_connection_success(self):
        """Test update_connection updates a connection."""
        app = FastAPI()
        register(app)

        mock_service = MagicMock()
        mock_service.update_connection = AsyncMock()

        mock_injector = MagicMock()
        mock_injector.get = MagicMock(return_value=mock_service)
        app.state.injector = mock_injector

        app.dependency_overrides[jwt_required] = lambda: {"sub": "testuser"}

        client = TestClient(app)
        response = client.put("/api/station-connections/507f1f77bcf86cd799439011", json={
            "name": "Updated Connection",
            "baseUrl": "https://api.example.com",
            "appId": "app123",
            "email": "test@example.com",
            "syncStationsOnPoll": False,
        })
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        app.dependency_overrides.clear()

    def test_update_connection_not_found_returns_404(self):
        """Test update_connection returns 404 when connection not found."""
        app = FastAPI()
        register(app)

        mock_service = MagicMock()
        mock_service.update_connection = AsyncMock(side_effect=ValueError("Not found"))

        mock_injector = MagicMock()
        mock_injector.get = MagicMock(return_value=mock_service)
        app.state.injector = mock_injector

        app.dependency_overrides[jwt_required] = lambda: {"sub": "testuser"}

        client = TestClient(app)
        response = client.put("/api/station-connections/507f1f77bcf86cd799439011", json={
            "name": "Updated Connection",
            "baseUrl": "https://api.example.com",
            "appId": "app123",
            "email": "test@example.com",
            "syncStationsOnPoll": False,
        })
        assert response.status_code == 404
        assert "Connection not found" in response.json()["detail"]

        app.dependency_overrides.clear()

    def test_delete_connection_success(self):
        """Test delete_connection deletes a connection."""
        app = FastAPI()
        register(app)

        mock_stations_repo = MagicMock()
        mock_stations_repo.count_by_connection = AsyncMock(return_value=0)

        mock_service = MagicMock()
        mock_service.delete_connection = AsyncMock()

        mock_injector = MagicMock()
        mock_injector.get = MagicMock(side_effect=lambda cls: mock_service if cls.__name__ == "StationConnectionsService" else mock_stations_repo)
        app.state.injector = mock_injector

        app.dependency_overrides[jwt_required] = lambda: {"sub": "testuser"}

        client = TestClient(app)
        response = client.delete("/api/station-connections/507f1f77bcf86cd799439011")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

        app.dependency_overrides.clear()

    def test_delete_connection_with_stations_returns_409(self):
        """Test delete_connection returns 409 when stations use the connection."""
        app = FastAPI()
        register(app)

        mock_stations_repo = MagicMock()
        mock_stations_repo.count_by_connection = AsyncMock(return_value=5)

        mock_service = MagicMock()
        mock_service.delete_connection = AsyncMock()

        mock_injector = MagicMock()
        mock_injector.get = MagicMock(side_effect=lambda cls: mock_service if cls.__name__ == "StationConnectionsService" else mock_stations_repo)
        app.state.injector = mock_injector

        app.dependency_overrides[jwt_required] = lambda: {"sub": "testuser"}

        client = TestClient(app)
        response = client.delete("/api/station-connections/507f1f77bcf86cd799439011")
        assert response.status_code == 409
        assert "Connection is used by 5 station(s)" in response.json()["detail"]

        app.dependency_overrides.clear()
