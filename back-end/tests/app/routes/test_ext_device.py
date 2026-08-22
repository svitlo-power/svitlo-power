"""Tests for app/routes/ext_device.py."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routes.ext_device import register
from app.utils.jwt_dependencies import jwt_reporter_only


class TestExtDeviceRoute:
    def test_register_adds_routes(self):
        app = FastAPI()
        register(app)
        routes = [r.path for r in app.routes]
        assert "/api/ext-device" in routes
        assert "/api/ext-device/ping" in routes

    def test_get_devices_exists(self):
        app = FastAPI()
        register(app)

        mock_injector = MagicMock()
        mock_ext_device = MagicMock()
        mock_ext_device.get_all_devices = AsyncMock(return_value=[])
        mock_settings = MagicMock()
        mock_settings.JWT_SECRET_KEY = "test-key"
        mock_injector.get = MagicMock(side_effect=lambda cls: mock_ext_device if cls.__name__ == "IExtDeviceService" else mock_settings)
        app.state.injector = mock_injector

        client = TestClient(app)
        response = client.get("/api/ext-device")
        # Should not return 404 (route exists)
        assert response.status_code != 404

    def test_device_ping_requires_reporter(self):
        app = FastAPI()
        register(app)

        mock_injector = MagicMock()
        mock_ext_device = MagicMock()
        mock_ext_device.process_ping_request = AsyncMock()
        mock_injector.get = MagicMock(return_value=mock_ext_device)
        app.state.injector = mock_injector

        client = TestClient(app)
        response = client.post("/api/ext-device/ping", json={
            "macAddress": "00:11:22:33:44:55",
            "fwVersion": "1.0.0",
            "fsVersion": "2.0.0",
            "uptime": 3600,
        })
        assert response.status_code == 401

    def test_get_devices_success(self):
        """Test get_devices returns device list."""
        app = FastAPI()
        register(app)

        from app.models.api import ExtDeviceResponse
        from beanie import PydanticObjectId
        from datetime import datetime, timezone
        mock_device = ExtDeviceResponse(
            mac_address="00:11:22:33:44:55",
            fw_version="1.0.0",
            fs_version="2.0.0",
            uptime=3600,
            updated_at=datetime.now(timezone.utc),
            user_id=None,
            grid_state=None,
        )

        mock_ext_device = MagicMock()
        mock_ext_device.get_all_devices = AsyncMock(return_value=[mock_device])

        mock_injector = MagicMock()
        mock_injector.get = MagicMock(return_value=mock_ext_device)
        app.state.injector = mock_injector

        client = TestClient(app)
        response = client.get("/api/ext-device")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["macAddress"] == "00:11:22:33:44:55"

    def test_get_devices_exception_returns_500(self):
        """Test get_devices returns 500 on exception."""
        app = FastAPI()
        register(app)

        mock_ext_device = MagicMock()
        mock_ext_device.get_all_devices = AsyncMock(side_effect=Exception("DB error"))

        mock_injector = MagicMock()
        mock_injector.get = MagicMock(return_value=mock_ext_device)
        app.state.injector = mock_injector

        client = TestClient(app)
        response = client.get("/api/ext-device")
        assert response.status_code == 500
        assert "Internal server error" in response.json()["detail"]

    def test_device_ping_success(self):
        """Test device_ping processes ping request."""
        app = FastAPI()
        register(app)

        mock_ext_device = MagicMock()
        mock_ext_device.process_ping_request = AsyncMock()

        mock_injector = MagicMock()
        mock_injector.get = MagicMock(return_value=mock_ext_device)
        app.state.injector = mock_injector

        app.dependency_overrides[jwt_reporter_only] = lambda: {"sub": "reporter_user"}

        client = TestClient(app)
        response = client.post("/api/ext-device/ping", json={
            "macAddress": "00:11:22:33:44:55",
            "fwVersion": "1.0.0",
            "fsVersion": "2.0.0",
            "uptime": 3600,
        })
        assert response.status_code == 200
        assert response.json()["status"] == "ok"

        app.dependency_overrides.clear()

    def test_device_ping_exception_returns_500(self):
        """Test device_ping returns 500 on exception."""
        app = FastAPI()
        register(app)

        mock_ext_device = MagicMock()
        mock_ext_device.process_ping_request = AsyncMock(side_effect=Exception("Processing error"))

        mock_injector = MagicMock()
        mock_injector.get = MagicMock(return_value=mock_ext_device)
        app.state.injector = mock_injector

        app.dependency_overrides[jwt_reporter_only] = lambda: {"sub": "reporter_user"}

        client = TestClient(app)
        response = client.post("/api/ext-device/ping", json={
            "macAddress": "00:11:22:33:44:55",
            "fwVersion": "1.0.0",
            "fsVersion": "2.0.0",
            "uptime": 3600,
        })
        assert response.status_code == 500
        assert "Internal server error" in response.json()["detail"]

        app.dependency_overrides.clear()
