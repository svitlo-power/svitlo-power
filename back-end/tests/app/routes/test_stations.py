"""Tests for app/routes/stations.py."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routes.stations import register
from app.utils.jwt_dependencies import jwt_required


class TestStationsRoute:
    def test_register_adds_routes(self):
        app = FastAPI()
        register(app)
        routes = [r.path for r in app.routes]
        assert "/api/stations/stations" in routes
        assert "/api/stations/save" in routes

    def test_get_stations_requires_jwt(self):
        app = FastAPI()
        register(app)

        client = TestClient(app)
        response = client.post("/api/stations/stations")
        assert response.status_code == 401

    def test_save_station_requires_jwt(self):
        app = FastAPI()
        register(app)

        client = TestClient(app)
        response = client.put("/api/stations/save", json={"id": "507f1f77bcf86cd799439011", "enabled": True, "order": 1})
        assert response.status_code == 401

    def test_get_stations_success(self):
        """Test get_stations returns station list."""
        app = FastAPI()
        register(app)

        mock_station = MagicMock()
        mock_station.id = "507f1f77bcf86cd799439011"
        mock_station.station_name = "Test Station"
        mock_station.station_alias = None
        mock_station.connection_status = "ONLINE"
        mock_station.grid_interconnection_type = "TYPE_A"
        mock_station.last_update_time = "2024-01-01T00:00:00Z"
        mock_station.battery_capacity = 500.0
        mock_station.enabled = True
        mock_station.order = 1
        mock_station.connection_id = "507f1f77bcf86cd799439011"

        mock_stations_service = MagicMock()
        mock_stations_service.get_stations = AsyncMock(return_value=[mock_station])

        mock_connections_service = MagicMock()
        mock_connections_service.get_connections = MagicMock(return_value=[])

        mock_injector = MagicMock()
        mock_injector.get = MagicMock(side_effect=lambda cls: mock_stations_service if cls.__name__ == "StationsService" else mock_connections_service)
        app.state.injector = mock_injector

        app.dependency_overrides[jwt_required] = lambda: {"sub": "testuser"}

        client = TestClient(app)
        response = client.post("/api/stations/stations")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["stationName"] == "Test Station"
        assert data[0]["connectionName"] is None

        app.dependency_overrides.clear()

    def test_get_stations_with_connection(self):
        """Test get_stations returns station with connection name."""
        app = FastAPI()
        register(app)

        mock_station = MagicMock()
        mock_station.id = "507f1f77bcf86cd799439011"
        mock_station.station_name = "Test Station"
        mock_station.station_alias = None
        mock_station.connection_status = "ONLINE"
        mock_station.grid_interconnection_type = "TYPE_A"
        mock_station.last_update_time = "2024-01-01T00:00:00Z"
        mock_station.battery_capacity = 500.0
        mock_station.enabled = True
        mock_station.order = 1
        mock_station.connection_id = "507f1f77bcf86cd799439011"

        mock_connection = MagicMock()
        mock_connection.id = "507f1f77bcf86cd799439011"
        mock_connection.name = "Deye Connection"

        mock_stations_service = MagicMock()
        mock_stations_service.get_stations = AsyncMock(return_value=[mock_station])

        mock_connections_service = MagicMock()
        mock_connections_service.get_connections = MagicMock(return_value=[mock_connection])

        mock_injector = MagicMock()
        mock_injector.get = MagicMock(side_effect=lambda cls: mock_stations_service if cls.__name__ == "StationsService" else mock_connections_service)
        app.state.injector = mock_injector

        app.dependency_overrides[jwt_required] = lambda: {"sub": "testuser"}

        client = TestClient(app)
        response = client.post("/api/stations/stations")
        assert response.status_code == 200
        data = response.json()
        assert data[0]["connectionName"] == "Deye Connection"

        app.dependency_overrides.clear()

    def test_get_stations_empty(self):
        """Test get_stations returns empty list."""
        app = FastAPI()
        register(app)

        mock_stations_service = MagicMock()
        mock_stations_service.get_stations = AsyncMock(return_value=[])

        mock_connections_service = MagicMock()
        mock_connections_service.get_connections = MagicMock(return_value=[])

        mock_injector = MagicMock()
        mock_injector.get = MagicMock(side_effect=lambda cls: mock_stations_service if cls.__name__ == "StationsService" else mock_connections_service)
        app.state.injector = mock_injector

        app.dependency_overrides[jwt_required] = lambda: {"sub": "testuser"}

        client = TestClient(app)
        response = client.post("/api/stations/stations")
        assert response.status_code == 200
        assert response.json() == []

        app.dependency_overrides.clear()

    def test_save_station_success(self):
        """Test save_station updates station."""
        app = FastAPI()
        register(app)

        mock_stations_service = MagicMock()
        mock_stations_service.edit_station = AsyncMock()

        mock_injector = MagicMock()
        mock_injector.get = MagicMock(return_value=mock_stations_service)
        app.state.injector = mock_injector

        app.dependency_overrides[jwt_required] = lambda: {"sub": "testuser"}

        client = TestClient(app)
        response = client.put("/api/stations/save", json={
            "id": "507f1f77bcf86cd799439011",
            "enabled": True,
            "order": 1,
            "batteryCapacity": 500.0,
            "alias": "My Station",
        })
        assert response.status_code == 200
        assert response.json()["success"] is True
        assert response.json()["id"] == "507f1f77bcf86cd799439011"

        app.dependency_overrides.clear()

    def test_save_station_defaults(self):
        """Test save_station uses default values."""
        app = FastAPI()
        register(app)

        mock_stations_service = MagicMock()
        mock_stations_service.edit_station = AsyncMock()

        mock_injector = MagicMock()
        mock_injector.get = MagicMock(return_value=mock_stations_service)
        app.state.injector = mock_injector

        app.dependency_overrides[jwt_required] = lambda: {"sub": "testuser"}

        client = TestClient(app)
        response = client.put("/api/stations/save", json={
            "id": "507f1f77bcf86cd799439011",
        })
        assert response.status_code == 200
        mock_stations_service.edit_station.assert_called_once()

        app.dependency_overrides.clear()
