"""Tests for app/settings.py."""
import os
from unittest.mock import patch, MagicMock

import pytest

from app.settings import Settings, ProductionSettings, DebugSettings, CONFIG_MAP, get_settings


# Environment variables from .env file for testing
ENV_VARS = {
    "SECRET_KEY": "hYEqTMUI1c3TyvwvaKYPSCFVwMl4BQhT",
    "JWT_SECRET_KEY": "hYEqTMUI1c3TyvwvaKYPSCFVwMl4BQhT",
    "DEYE_BASE_URL": "https://eu1-developer.deyecloud.com/v1.0",
    "DEYE_APP_ID": "202411296579004",
    "DEYE_APP_SECRET": "5b166b1871c80593931ba732a70550df",
    "DEYE_EMAIL": "admin.svitlopark@gmail.com",
    "DEYE_PASSWORD": "b!k8QA6Kc&dk?nx@",
    "DEYE_FETCH_INTERVAL": "180",
    "DEYE_SYNC_STATIONS_ON_POLL": "true",
    "DEYE_ASSUMED_OFFLINE_REPORTS": "3",
    "TG_HOOK_BASE_URL": "https://svitlo-bot-test.svitlopark-3-30.keenetic.pro/",
    "BOT_TIMEZONE": "Europe/Kyiv",
    "STATISTIC_KEEP_DAYS": "365",
    "DEBUG": "True",
}


@pytest.fixture(autouse=True)
def mock_env():
    """Mock environment variables for Settings tests."""
    with patch.dict(os.environ, ENV_VARS, clear=False):
        yield


class TestSettings:
    def test_secret_key_from_env(self):
        """Test that SECRET_KEY is loaded from .env file."""
        settings = Settings(MONGO_URI="mongodb://localhost:27017")
        assert settings.SECRET_KEY is not None
        # Value from .env file
        assert len(settings.SECRET_KEY) == 32

    def test_jwt_secret_key_from_env(self):
        """Test that JWT_SECRET_KEY is loaded from .env file."""
        settings = Settings(MONGO_URI="mongodb://localhost:27017")
        assert settings.JWT_SECRET_KEY is not None
        # Value from .env file (32 chars, not 64 as default)
        assert len(settings.JWT_SECRET_KEY) == 32

    def test_deye_fetch_interval_from_env(self):
        """Test DEYE_FETCH_INTERVAL from .env file."""
        settings = Settings(MONGO_URI="mongodb://localhost:27017")
        # Value from .env file
        assert settings.DEYE_FETCH_INTERVAL == 180

    def test_deye_sync_stations_on_poll_from_env(self):
        """Test DEYE_SYNC_STATIONS_ON_POLL from .env file."""
        settings = Settings(MONGO_URI="mongodb://localhost:27017")
        # Value from .env file
        assert settings.DEYE_SYNC_STATIONS_ON_POLL is True

    def test_default_deye_report_interval(self):
        """Test DEYE_REPORT_INTERVAL default value."""
        settings = Settings(MONGO_URI="mongodb://localhost:27017")
        assert settings.DEYE_REPORT_INTERVAL == 300

    def test_deye_assumed_offline_reports_from_env(self):
        """Test DEYE_ASSUMED_OFFLINE_REPORTS from .env file."""
        settings = Settings(MONGO_URI="mongodb://localhost:27017")
        # Value from .env file
        assert settings.DEYE_ASSUMED_OFFLINE_REPORTS == 3

    def test_bot_timezone_from_env(self):
        """Test BOT_TIMEZONE from .env file."""
        settings = Settings(MONGO_URI="mongodb://localhost:27017")
        # Value from .env file
        assert settings.BOT_TIMEZONE == "Europe/Kyiv"

    def test_default_host(self):
        """Test HOST default value."""
        settings = Settings(MONGO_URI="mongodb://localhost:27017")
        assert settings.HOST == "127.0.0.1"

    def test_statistic_keep_days_from_env(self):
        """Test STATISTIC_KEEP_DAYS from .env file."""
        settings = Settings(MONGO_URI="mongodb://localhost:27017")
        # Value from .env file
        assert settings.STATISTIC_KEEP_DAYS == 365

    def test_default_sse_ping_interval(self):
        """Test SSE_PING_INTERVAL default value."""
        settings = Settings(MONGO_URI="mongodb://localhost:27017")
        assert settings.SSE_PING_INTERVAL == 45

    def test_deye_fields_from_env(self):
        """Test DEYE fields from .env file."""
        settings = Settings(MONGO_URI="mongodb://localhost:27017")
        assert settings.DEYE_BASE_URL == "https://eu1-developer.deyecloud.com/v1.0"
        assert settings.DEYE_APP_ID == "202411296579004"
        assert settings.DEYE_APP_SECRET == "5b166b1871c80593931ba732a70550df"
        assert settings.DEYE_EMAIL == "admin.svitlopark@gmail.com"
        assert settings.DEYE_PASSWORD == "b!k8QA6Kc&dk?nx@"

    def test_admin_fields_default_none(self):
        """Test ADMIN fields default to None."""
        settings = Settings(MONGO_URI="mongodb://localhost:27017")
        assert settings.ADMIN_USER is None
        assert settings.ADMIN_PASSWORD is None

    def test_tg_hook_base_url_from_env(self):
        """Test TG_HOOK_BASE_URL from .env file."""
        settings = Settings(MONGO_URI="mongodb://localhost:27017")
        # Value from .env file
        assert settings.TG_HOOK_BASE_URL == "https://svitlo-bot-test.svitlopark-3-30.keenetic.pro/"


class TestProductionSettings:
    def test_debug_is_false(self):
        """Test ProductionSettings has DEBUG=False by default."""
        with patch.dict(os.environ, {"DEBUG": "False"}):
            settings = ProductionSettings(MONGO_URI="mongodb://localhost:27017")
            assert settings.DEBUG is False

    def test_session_cookie_httponly(self):
        """Test ProductionSettings has SESSION_COOKIE_HTTPONLY=True."""
        settings = ProductionSettings(MONGO_URI="mongodb://localhost:27017")
        assert settings.SESSION_COOKIE_HTTPONLY is True

    def test_remember_cookie_httponly(self):
        """Test ProductionSettings has REMEMBER_COOKIE_HTTPONLY=True."""
        settings = ProductionSettings(MONGO_URI="mongodb://localhost:27017")
        assert settings.REMEMBER_COOKIE_HTTPONLY is True

    def test_remember_cookie_duration(self):
        """Test ProductionSettings has REMEMBER_COOKIE_DURATION=3600."""
        settings = ProductionSettings(MONGO_URI="mongodb://localhost:27017")
        assert settings.REMEMBER_COOKIE_DURATION == 3600


class TestDebugSettings:
    def test_debug_is_true(self):
        """Test DebugSettings has DEBUG=True."""
        settings = DebugSettings(MONGO_URI="mongodb://localhost:27017")
        assert settings.DEBUG is True

    def test_host_from_env(self):
        """Test DebugSettings reads HOST from DEBUG_HOST env var."""
        with patch.dict(os.environ, {"DEBUG_HOST": "0.0.0.0"}):
            settings = DebugSettings(MONGO_URI="mongodb://localhost:27017")
            assert settings.HOST == "0.0.0.0"

    def test_host_default_when_no_env(self):
        """Test DebugSettings uses default HOST when DEBUG_HOST not set."""
        settings = DebugSettings(MONGO_URI="mongodb://localhost:27017")
        assert settings.HOST == "127.0.0.1"


class TestConfigMap:
    def test_config_map_has_production(self):
        """Test CONFIG_MAP has Production key."""
        assert "Production" in CONFIG_MAP

    def test_config_map_has_debug(self):
        """Test CONFIG_MAP has Debug key."""
        assert "Debug" in CONFIG_MAP

    def test_config_map_values_are_correct_classes(self):
        """Test CONFIG_MAP values are correct classes."""
        assert CONFIG_MAP["Production"] is ProductionSettings
        assert CONFIG_MAP["Debug"] is DebugSettings


class TestGetSettings:
    def test_get_settings_returns_production_by_default(self):
        """Test get_settings returns ProductionSettings by default."""
        get_settings.cache_clear()
        with patch.dict(os.environ, {"DEBUG": "False", "MONGO_URI": "mongodb://localhost:27017"}):
            settings = get_settings()
            assert isinstance(settings, ProductionSettings)

    def test_get_settings_returns_debug_when_debug_env(self):
        """Test get_settings returns DebugSettings when DEBUG=True."""
        get_settings.cache_clear()
        with patch.dict(os.environ, {"DEBUG": "True", "MONGO_URI": "mongodb://localhost:27017"}):
            settings = get_settings()
            assert isinstance(settings, DebugSettings)

    def test_get_settings_is_cached(self):
        """Test get_settings returns cached instance."""
        get_settings.cache_clear()
        with patch.dict(os.environ, {"DEBUG": "False", "MONGO_URI": "mongodb://localhost:27017"}):
            settings1 = get_settings()
            settings2 = get_settings()
            assert settings1 is settings2