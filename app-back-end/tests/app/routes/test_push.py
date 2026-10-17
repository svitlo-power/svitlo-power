"""Tests for push device routes."""
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient
from beanie import PydanticObjectId

from app.main import create_app
from app.settings import Settings
from shared.services import PushDevicesService
from shared.models.api.push import PushDeviceResponse, PushTopicResponse


@pytest.fixture
def mock_settings():
    settings = MagicMock(spec=Settings)
    settings.DEBUG = True
    return settings


@pytest.fixture
def mock_push_service():
    return AsyncMock(spec=PushDevicesService)


@pytest.fixture
def app(mock_settings, mock_push_service):
    from fastapi_injector import InjectorMiddleware, attach_injector
    from injector import Injector, Module, provider
    from app.container import AppModule

    class TestModule(Module):
        @provider
        def provide_push_devices_service(self) -> PushDevicesService:
            return mock_push_service

    injector = Injector([AppModule(), TestModule()])
    app = create_app(mock_settings)
    app.add_middleware(InjectorMiddleware, injector=injector)
    attach_injector(app, injector)
    return app


@pytest.fixture
def client(app):
    return TestClient(app)


@pytest.fixture
def device():
    now = datetime.now(timezone.utc)
    return PushDeviceResponse(
        id=PydanticObjectId(),
        platform="android",
        language="uk",
        enabled=True,
        disabled_topics=["battery_low"],
        buildings=[],
        app_version="2.1.1",
        created_at=now,
        last_seen=now,
    )


class TestPushRoutes:
    def test_register_device(self, client, mock_push_service, device):
        mock_push_service.register_device.return_value = device

        response = client.post("/api/push/devices", json={
            "token": "tok", "platform": "android", "language": "en", "appVersion": "2.1.1",
        })

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(device.id)
        assert data["disabledTopics"] == ["battery_low"]
        request = mock_push_service.register_device.call_args.args[0]
        assert request.token == "tok"
        assert request.language == "en"
        assert request.app_version == "2.1.1"

    def test_register_device_rejects_unknown_platform(self, client, mock_push_service):
        response = client.post("/api/push/devices", json={"token": "tok", "platform": "ios"})

        assert response.status_code == 422
        mock_push_service.register_device.assert_not_called()

    def test_get_current_device(self, client, mock_push_service, device):
        mock_push_service.get_device.return_value = device

        response = client.post("/api/push/devices/current", json={"token": "tok"})

        assert response.status_code == 200
        mock_push_service.get_device.assert_awaited_once_with("tok")

    def test_get_current_device_not_registered(self, client, mock_push_service):
        mock_push_service.get_device.return_value = None

        response = client.post("/api/push/devices/current", json={"token": "tok"})

        assert response.status_code == 404

    def test_update_subscriptions(self, client, mock_push_service, device):
        mock_push_service.update_subscriptions.return_value = device

        response = client.post("/api/push/devices/subscriptions", json={
            "token": "tok", "enabled": True, "disabledTopics": ["battery_low"],
        })

        assert response.status_code == 200
        request = mock_push_service.update_subscriptions.call_args.args[0]
        assert request.disabled_topics == ["battery_low"]

    def test_update_subscriptions_not_registered(self, client, mock_push_service):
        mock_push_service.update_subscriptions.return_value = None

        response = client.post("/api/push/devices/subscriptions", json={"token": "tok"})

        assert response.status_code == 404

    def test_unregister_device(self, client, mock_push_service):
        mock_push_service.unregister_device.return_value = True

        response = client.post("/api/push/devices/unregister", json={"token": "tok"})

        assert response.status_code == 200
        assert response.json() == {"success": True}
        mock_push_service.unregister_device.assert_awaited_once_with("tok")

    def test_get_topics(self, client, mock_push_service):
        mock_push_service.get_enabled_topics.return_value = [
            PushTopicResponse(key="announcements", name={"uk": "Оголошення"}, description={"uk": "Опис"}),
        ]

        response = client.get("/api/push/topics")

        assert response.status_code == 200
        assert response.json() == [{"key": "announcements", "name": {"uk": "Оголошення"}, "description": {"uk": "Опис"}}]

    def test_admin_endpoints_not_exposed(self, client):
        assert client.post("/api/push/test", json={"title": "t", "body": "b"}).status_code in (404, 405)
        assert client.get("/api/push/devices").status_code in (404, 405)
