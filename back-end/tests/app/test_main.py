"""Tests for app/main.py."""
from unittest.mock import MagicMock, patch

from fastapi import FastAPI

from app.main import create_app
from app.settings import Settings


class TestCreateApp:
    def test_create_app_returns_fastapi_instance(self):
        settings = MagicMock(spec=Settings)
        settings.DEBUG = False
        app = create_app(settings)
        assert isinstance(app, FastAPI)

    def test_create_app_sets_title(self):
        settings = MagicMock(spec=Settings)
        settings.DEBUG = False
        app = create_app(settings)
        assert app.title == "SvitloPower"

    def test_create_app_sets_version(self):
        settings = MagicMock(spec=Settings)
        settings.DEBUG = False
        app = create_app(settings)
        assert app.version == "1.1.6"

    def test_create_app_sets_debug(self):
        settings = MagicMock(spec=Settings)
        settings.DEBUG = True
        app = create_app(settings)
        assert app.debug is True

    def test_create_app_sets_settings_on_state(self):
        settings = MagicMock(spec=Settings)
        settings.DEBUG = False
        app = create_app(settings)
        assert app.state.settings is settings

    def test_create_app_adds_language_middleware(self):
        settings = MagicMock(spec=Settings)
        settings.DEBUG = False
        app = create_app(settings)
        # Check that middleware was added
        middleware_classes = [m.cls for m in app.user_middleware]
        from app.middlewares.language import LanguageMiddleware
        assert LanguageMiddleware in middleware_classes
