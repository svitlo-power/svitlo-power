"""Tests for app settings."""
import pytest
from unittest.mock import patch, MagicMock
import os

from app.settings import Settings, ProductionSettings, DebugSettings, get_settings, CONFIG_MAP


class TestSettings:
    def test_settings_defaults(self):
        # Test with a clean environment - we need to clear the .env file influence
        with patch.dict(os.environ, {
            "PORT": "8000",
            "DEBUG": "False",
            "JWT_SECRET_KEY": "",
            "SECRET_KEY": "",
            "REDIS_URI": "redis://localhost:6379/0",
            "MONGO_URI": "mongodb://localhost:27017/?directConnection=true",
            "MONGO_DB": "svitlo-power",
            "DEYE_BASE_URL": "https://eu1-developer.deyecloud.com/v1.0",
            "DEYE_APP_ID": "",
            "DEYE_APP_SECRET": "",
            "DEYE_EMAIL": "",
            "DEYE_PASSWORD": "",
            "DEYE_FETCH_INTERVAL": "180",
            "DEYE_SYNC_STATIONS_ON_POLL": "True",
            "DEYE_ASSUMED_OFFLINE_REPORTS": "3",
            "TG_HOOK_BASE_URL": "",
            "BOT_TIMEZONE": "Europe/Kyiv",
            "STATISTIC_KEEP_DAYS": "365",
        }, clear=True):
            settings = Settings()
            assert settings.HOST == "0.0.0.0"
            assert settings.PORT == 8000
            assert settings.YASNO_REGION == 1
            assert settings.YASNO_DSO == 1
            assert settings.JWT_ALGORITHM == "HS256"
            assert settings.JWT_EXPIRE_MINUTES == 60 * 24 * 30
            assert settings.MONGO_URI == "mongodb://localhost:27017/?directConnection=true"
            assert settings.MONGO_DB == "svitlo-power"
            assert settings.REDIS_URI == "redis://localhost:6379/0"

    def test_settings_from_env(self):
        with patch.dict(os.environ, {
            "HOST": "127.0.0.1",
            "PORT": "9000",
            "YASNO_REGION": "2",
            "YASNO_DSO": "3",
            "JWT_SECRET": "test-secret",
            "JWT_ALGORITHM": "RS256",
            "JWT_EXPIRE_MINUTES": "120",
            "MONGO_URI": "mongodb://test:27017",
            "MONGO_DB": "test-db",
            "REDIS_URI": "redis://test:6379/1",
        }, clear=True):
            settings = Settings()
            assert settings.HOST == "127.0.0.1"
            assert settings.PORT == 9000
            assert settings.YASNO_REGION == 2
            assert settings.YASNO_DSO == 3
            assert settings.JWT_SECRET == "test-secret"
            assert settings.JWT_ALGORITHM == "RS256"
            assert settings.JWT_EXPIRE_MINUTES == 120
            assert settings.MONGO_URI == "mongodb://test:27017"
            assert settings.MONGO_DB == "test-db"
            assert settings.REDIS_URI == "redis://test:6379/1"

    def test_production_settings(self):
            with patch.dict(os.environ, {
                "DEBUG": "False",
                "PORT": "8000",
                "JWT_SECRET_KEY": "test-secret",
                "SECRET_KEY": "test-secret",
                "REDIS_URI": "redis://localhost:6379/0",
                "MONGO_URI": "mongodb://localhost:27017/?directConnection=true",
                "MONGO_DB": "svitlo-power",
                "DEYE_BASE_URL": "https://eu1-developer.deyecloud.com/v1.0",
                "DEYE_APP_ID": "test-app-id",
                "DEYE_APP_SECRET": "test-app-secret",
                "DEYE_EMAIL": "test@example.com",
                "DEYE_PASSWORD": "test-password",
                "DEYE_FETCH_INTERVAL": "180",
                "DEYE_SYNC_STATIONS_ON_POLL": "True",
                "DEYE_ASSUMED_OFFLINE_REPORTS": "3",
                "TG_HOOK_BASE_URL": "",
                "BOT_TIMEZONE": "Europe/Kyiv",
                "STATISTIC_KEEP_DAYS": "365",
            }, clear=True):
                settings = ProductionSettings()
                assert settings.DEBUG is False

    def test_debug_settings(self):
        settings = DebugSettings()
        assert settings.DEBUG is True

    def test_config_map(self):
        assert "Production" in CONFIG_MAP
        assert "Debug" in CONFIG_MAP
        assert CONFIG_MAP["Production"] == ProductionSettings
        assert CONFIG_MAP["Debug"] == DebugSettings

    def test_get_settings_production(self):
        with patch.dict(os.environ, {"DEBUG": "False"}, clear=True):
            # Clear the lru_cache
            get_settings.cache_clear()
            settings = get_settings()
            assert isinstance(settings, ProductionSettings)
            assert settings.DEBUG is False

    def test_get_settings_debug(self):
        with patch.dict(os.environ, {"DEBUG": "True"}, clear=True):
            get_settings.cache_clear()
            settings = get_settings()
            assert isinstance(settings, DebugSettings)
            assert settings.DEBUG is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])