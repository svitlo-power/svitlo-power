"""Tests for app/routes/stations_data.py."""
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routes.stations_data import register
from app.utils.jwt_dependencies import jwt_required


class TestStationsDataRoute:
    def test_register_adds_routes(self):
        app = FastAPI()
        register(app)
        routes = [r.path for r in app.routes]
        assert "/api/stationsData/stationsData" in routes
        assert "/api/stationsData/stationDetails/{station_id}" in routes

    def test_get_stations_data_requires_jwt(self):
        app = FastAPI()
        register(app)

        client = TestClient(app)
        response = client.post("/api/stationsData/stationsData", json={
            "lastSeconds": 3600,
            "pageSize": 10,
            "page": 1,
            "column": "test",
            "dataType": 2,
            "order": "asc",
        })
        assert response.status_code == 401

    def test_get_stations_data_with_last_seconds(self):
        """Test get_stations_data with lastSeconds returns station data."""
        app = FastAPI()
        register(app)

        mock_station = MagicMock()
        mock_station.id = "507f1f77bcf86cd799439011"
        mock_station.station_name = "Test Station"

        mock_data = MagicMock()
        mock_data.battery_soc = 85.0
        mock_data.discharge_power = 100.0
        mock_data.charge_power = 0.0
        mock_data.consumption_power = 50.0
        mock_data.last_update_time = datetime.now(timezone.utc)

        mock_stations = MagicMock()
        mock_stations.get_stations_data = AsyncMock(return_value=[(mock_station, [mock_data])])

        mock_injector = MagicMock()
        mock_injector.get = MagicMock(return_value=mock_stations)
        app.state.injector = mock_injector

        app.dependency_overrides[jwt_required] = lambda: {"sub": "testuser"}

        client = TestClient(app)
        response = client.post("/api/stationsData/stationsData", json={
            "lastSeconds": 3600,
            "recordsCount": 250,
        })
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "Test Station"
        assert len(data[0]["data"]) == 1
        assert data[0]["data"][0]["batterySoc"] == 85.0

        app.dependency_overrides.clear()

    def test_get_stations_data_with_range(self):
        """Test get_stations_data with start/end date returns station data."""
        app = FastAPI()
        register(app)

        mock_station = MagicMock()
        mock_station.id = "507f1f77bcf86cd799439011"
        mock_station.station_name = "Test Station"

        mock_data = MagicMock()
        mock_data.battery_soc = 85.0
        mock_data.discharge_power = 100.0
        mock_data.charge_power = 0.0
        mock_data.consumption_power = 50.0
        mock_data.last_update_time = datetime.now(timezone.utc)

        mock_stations = MagicMock()
        mock_stations.get_stations_data_range = AsyncMock(return_value=[(mock_station, [mock_data])])

        mock_injector = MagicMock()
        mock_injector.get = MagicMock(return_value=mock_stations)
        app.state.injector = mock_injector

        app.dependency_overrides[jwt_required] = lambda: {"sub": "testuser"}

        client = TestClient(app)
        response = client.post("/api/stationsData/stationsData", json={
            "startDate": "2024-01-01T00:00:00Z",
            "endDate": "2024-01-02T00:00:00Z",
            "recordsCount": 250,
        })
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["name"] == "Test Station"

        app.dependency_overrides.clear()

    def test_get_stations_data_downsample(self):
        """Test get_stations_data with downsampling when records exceed max."""
        app = FastAPI()
        register(app)

        mock_station = MagicMock()
        mock_station.id = "507f1f77bcf86cd799439011"
        mock_station.station_name = "Test Station"

        now = datetime.now(timezone.utc)
        mock_data = []
        for i in range(10):
            d = MagicMock()
            d.battery_soc = 80.0 + i
            d.discharge_power = 100.0
            d.charge_power = 0.0
            d.consumption_power = 50.0
            d.last_update_time = now - timedelta(minutes=10 - i)
            mock_data.append(d)

        mock_stations = MagicMock()
        mock_stations.get_stations_data = AsyncMock(return_value=[(mock_station, mock_data)])

        mock_injector = MagicMock()
        mock_injector.get = MagicMock(return_value=mock_stations)
        app.state.injector = mock_injector

        app.dependency_overrides[jwt_required] = lambda: {"sub": "testuser"}

        client = TestClient(app)
        response = client.post("/api/stationsData/stationsData", json={
            "lastSeconds": 3600,
            "recordsCount": 5,
        })
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        # With 10 records and max 5, should be downsampled
        assert len(data[0]["data"]) <= 5

        app.dependency_overrides.clear()

    def test_get_stations_data_downsample_single_record(self):
        """Test downsample with max_records=1 (n_segments <= 0)."""
        app = FastAPI()
        register(app)

        mock_station = MagicMock()
        mock_station.id = "507f1f77bcf86cd799439011"
        mock_station.station_name = "Test Station"

        now = datetime.now(timezone.utc)
        mock_data = []
        for i in range(5):
            d = MagicMock()
            d.battery_soc = 80.0 + i
            d.discharge_power = 100.0
            d.charge_power = 0.0
            d.consumption_power = 50.0
            d.last_update_time = now - timedelta(minutes=5 - i)
            mock_data.append(d)

        mock_stations = MagicMock()
        mock_stations.get_stations_data = AsyncMock(return_value=[(mock_station, mock_data)])

        mock_injector = MagicMock()
        mock_injector.get = MagicMock(return_value=mock_stations)
        app.state.injector = mock_injector

        app.dependency_overrides[jwt_required] = lambda: {"sub": "testuser"}

        client = TestClient(app)
        response = client.post("/api/stationsData/stationsData", json={
            "lastSeconds": 3600,
            "recordsCount": 1,
        })
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        # With max_records=1, n_segments = -1, should return [data[0], data[-1]]
        assert len(data[0]["data"]) == 2

        app.dependency_overrides.clear()

    def test_get_stations_data_empty(self):
        """Test get_stations_data with no stations."""
        app = FastAPI()
        register(app)

        mock_stations = MagicMock()
        mock_stations.get_stations_data = AsyncMock(return_value=[])

        mock_injector = MagicMock()
        mock_injector.get = MagicMock(return_value=mock_stations)
        app.state.injector = mock_injector

        app.dependency_overrides[jwt_required] = lambda: {"sub": "testuser"}

        client = TestClient(app)
        response = client.post("/api/stationsData/stationsData", json={
            "lastSeconds": 3600,
            "recordsCount": 250,
        })
        assert response.status_code == 200
        assert response.json() == []

        app.dependency_overrides.clear()

    def test_get_station_details_success(self):
        """Test get_station_details returns station details."""
        app = FastAPI()
        register(app)

        mock_station = MagicMock()
        mock_station.id = "507f1f77bcf86cd799439011"
        mock_station.station_id = 12345
        mock_station.station_name = "Test Station"
        mock_station.connection_status = "ONLINE"
        mock_station.grid_interconnection_type = "TYPE_A"
        mock_station.installed_capacity = 1000.0
        mock_station.battery_capacity = 500.0
        mock_station.last_update_time = datetime.now(timezone.utc)

        mock_data = MagicMock()
        mock_data.id = "507f1f77bcf86cd799439011"
        mock_data.station_id = 12345
        mock_data.battery_power = 100.0
        mock_data.battery_soc = 85.0
        mock_data.charge_power = 200.0
        mock_data.code = "CODE"
        mock_data.consumption_power = 50.0
        mock_data.discharge_power = 100.0
        mock_data.generation_power = 300.0
        mock_data.grid_power = 50.0
        mock_data.irradiate_intensity = 800.0
        mock_data.last_update_time = datetime.now(timezone.utc)
        mock_data.msg = "test"
        mock_data.purchase_power = 60.0
        mock_data.request_id = "req123"
        mock_data.wire_power = 70.0

        mock_stations = MagicMock()
        mock_stations.get_station_data = AsyncMock(return_value=(mock_station, [mock_data]))

        mock_injector = MagicMock()
        mock_injector.get = MagicMock(return_value=mock_stations)
        app.state.injector = mock_injector

        app.dependency_overrides[jwt_required] = lambda: {"sub": "testuser"}

        client = TestClient(app)
        response = client.post("/api/stationsData/stationDetails/507f1f77bcf86cd799439011", json={
            "lastSeconds": 3600,
        })
        assert response.status_code == 200
        data = response.json()
        assert "station" in data
        assert data["station"]["stationName"] == "Test Station"
        assert len(data["data"]) == 1
        assert data["dataCount"] == 1

        app.dependency_overrides.clear()

    def test_get_station_details_not_found(self):
        """Test get_station_details returns 404 when station not found."""
        app = FastAPI()
        register(app)

        mock_stations = MagicMock()
        mock_stations.get_station_data = AsyncMock(return_value=(None, None))

        mock_injector = MagicMock()
        mock_injector.get = MagicMock(return_value=mock_stations)
        app.state.injector = mock_injector

        app.dependency_overrides[jwt_required] = lambda: {"sub": "testuser"}

        client = TestClient(app)
        response = client.post("/api/stationsData/stationDetails/507f1f77bcf86cd799439011", json={
            "lastSeconds": 3600,
        })
        assert response.status_code == 404
        assert "Station not found" in response.json()["detail"]

        app.dependency_overrides.clear()

    def test_get_station_details_requires_jwt(self):
        """Test get_station_details requires JWT."""
        app = FastAPI()
        register(app)

        client = TestClient(app)
        response = client.post("/api/stationsData/stationDetails/507f1f77bcf86cd799439011", json={
            "lastSeconds": 3600,
        })
        assert response.status_code == 401
