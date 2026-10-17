"""Tests for app/routes/push.py."""
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

from beanie import PydanticObjectId
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routes.push import register
from app.models.api import PushDeviceResponse, PushSendResult


def _client(push):
    app = FastAPI()
    register(app)
    settings = MagicMock()
    settings.JWT_SECRET_KEY = "test-key"
    injector = MagicMock()
    injector.get = MagicMock(side_effect=lambda cls: push if cls.__name__ == "PushService" else settings)
    app.state.injector = injector
    return TestClient(app)


def _device_response():
    now = datetime.now(timezone.utc)
    return PushDeviceResponse(
        id=PydanticObjectId(), platform="android", language="uk", enabled=True,
        disabled_topics=[], buildings=[], created_at=now, last_seen=now,
    )


class TestPushRoutes:
    def test_register_adds_routes(self):
        app = FastAPI()
        register(app)
        routes = [r.path for r in app.routes]
        for path in ["/api/push/devices", "/api/push/devices/current", "/api/push/devices/subscriptions",
                     "/api/push/devices/unregister", "/api/push/test", "/api/push/topics",
                     "/api/push/topics/all", "/api/push/topics/{key}/state"]:
            assert path in routes

    def test_register_device_is_public(self):
        push = MagicMock()
        push.register_device = AsyncMock(return_value=_device_response())
        response = _client(push).post("/api/push/devices", json={"token": "tok", "platform": "android"})
        assert response.status_code == 200
        assert "token" not in response.json()

    def test_register_device_rejects_unknown_platform(self):
        response = _client(MagicMock()).post("/api/push/devices", json={"token": "tok", "platform": "ios"})
        assert response.status_code == 422

    def test_subscriptions_unknown_device_returns_404(self):
        push = MagicMock()
        push.update_subscriptions = AsyncMock(return_value=None)
        response = _client(push).post("/api/push/devices/subscriptions", json={"token": "tok"})
        assert response.status_code == 404

    def test_admin_endpoints_require_auth(self):
        push = MagicMock()
        push.send_to_all = AsyncMock(return_value=PushSendResult(success_count=0, failure_count=0, removed_count=0))
        client = _client(push)
        assert client.get("/api/push/devices").status_code == 401
        assert client.delete(f"/api/push/devices/{PydanticObjectId()}").status_code == 401
        assert client.post("/api/push/test", json={"title": "t", "body": "b"}).status_code == 401
        assert client.get("/api/push/topics/all").status_code == 401
        assert client.patch("/api/push/topics/announcements/state", json={"enabled": False}).status_code == 401
        push.send_to_all.assert_not_called()

    def test_public_topics(self):
        from app.models.api import PushTopicResponse
        push = MagicMock()
        push.get_enabled_topics = AsyncMock(return_value=[
            PushTopicResponse(key="announcements", name={"uk": "Оголошення"}, description={"uk": "Опис"}),
        ])
        response = _client(push).get("/api/push/topics")
        assert response.status_code == 200
        assert response.json()[0]["key"] == "announcements"
