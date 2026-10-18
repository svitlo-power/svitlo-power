"""Tests for the app access token check."""
import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient

from app.main import create_app
from app.settings import Settings
from shared.services import PushDevicesService


def make_client(token):
    from fastapi_injector import InjectorMiddleware, attach_injector
    from injector import Injector, Module, provider
    from app.container import AppModule

    push_service = AsyncMock(spec=PushDevicesService)
    push_service.get_enabled_topics.return_value = []

    class TestModule(Module):
        @provider
        def provide_push_devices_service(self) -> PushDevicesService:
            return push_service

    settings = MagicMock(spec=Settings)
    settings.DEBUG = True
    settings.APP_ACCESS_TOKEN = token
    injector = Injector([AppModule(), TestModule()])
    app = create_app(settings)
    app.add_middleware(InjectorMiddleware, injector=injector)
    attach_injector(app, injector)
    return TestClient(app)


class TestAppToken:
    @pytest.mark.parametrize("token", [None, ""])
    def test_check_disabled_without_configured_token(self, token):
        assert make_client(token).get("/api/push/topics").status_code == 200

    def test_accepts_valid_token(self):
        response = make_client("secret").get("/api/push/topics", headers={"X-App-Token": "secret"})
        assert response.status_code == 200

    def test_rejects_missing_token(self):
        assert make_client("secret").get("/api/push/topics").status_code == 401

    def test_rejects_wrong_token(self):
        response = make_client("secret").get("/api/push/topics", headers={"X-App-Token": "nope"})
        assert response.status_code == 401
