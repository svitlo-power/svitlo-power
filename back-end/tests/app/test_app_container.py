"""Tests for app/app_container.py."""
from unittest.mock import MagicMock, patch

from fastapi import FastAPI
from injector import singleton

from app.app_container import AppContainer, _create_containers, init_container, bind_client_session
from app.settings import Settings


class TestAppContainer:
    def test_init_stores_settings(self):
        settings = MagicMock(spec=Settings)
        container = AppContainer(settings)
        assert container._settings is settings

    def test_configure_binds_settings(self):
        settings = MagicMock(spec=Settings)
        container = AppContainer(settings)
        binder = MagicMock()
        container.configure(binder)
        binder.bind.assert_any_call(Settings, to=settings, scope=singleton)


class TestCreateContainers:
    def test_create_containers_returns_list(self):
        settings = MagicMock(spec=Settings)
        containers = _create_containers(settings)
        assert len(containers) == 3
        assert isinstance(containers[0], AppContainer)


class TestInitContainer:
    def test_init_container_returns_injector(self):
        app = FastAPI()
        settings = MagicMock(spec=Settings)
        settings.MONGO_URI = "mongodb://localhost:27017"
        settings.MONGO_DB = "test-db"
        settings.REDIS_URI = "redis://localhost:6379"
        settings.DEBUG = False
        settings.I18N_PATH = "../shared/i18n"

        with patch("app.app_container.attach_injector") as mock_attach, \
             patch("app.app_container._create_containers") as mock_create:
            mock_injector = MagicMock()
            mock_create.return_value = []
            injector = init_container(app, settings)
            mock_attach.assert_called_once()
            assert injector is not None


class TestBindClientSession:
    def test_bind_client_session_binds_session(self):
        injector = MagicMock()
        injector.binder = MagicMock()

        with patch("app.app_container.ClientSession") as mock_session_cls:
            mock_session = MagicMock()
            mock_session_cls.return_value = mock_session
            bind_client_session(injector)
            injector.binder.bind.assert_called_once()
