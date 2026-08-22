"""Tests for app/services/container.py."""
from unittest.mock import MagicMock, patch

import pytest
from injector import Binder, singleton, noscope

from app.services.container import ServicesContainer
from app.settings import Settings


class TestServicesContainer:
    def test_init_stores_settings(self):
        """Test that ServicesContainer stores settings."""
        settings = MagicMock(spec=Settings)
        container = ServicesContainer(settings)
        assert container._settings is settings

    def test_configure_binds_all_services(self):
        """Test that configure binds all expected services."""
        settings = MagicMock(spec=Settings)
        settings.MONGO_URI = "mongodb://localhost:27017"
        settings.MONGO_DB = "test-db"
        settings.REDIS_URI = "redis://localhost:6379"
        settings.DEBUG = False
        settings.I18N_PATH = "../shared/i18n"

        container = ServicesContainer(settings)
        binder = MagicMock(spec=Binder)

        with patch("app.services.container.BeanieInitializer") as mock_beanie_cls, \
             patch("app.services.container.EventsService") as mock_events_cls, \
             patch("app.services.container.EventsServiceConfig") as mock_config_cls, \
             patch("app.services.container.AsyncIOScheduler") as mock_scheduler_cls, \
             patch("app.services.container.TranslationService") as mock_ts_cls:
            mock_beanie_cls.return_value = MagicMock()
            mock_config_cls.return_value = MagicMock()
            mock_events_cls.return_value = MagicMock()
            mock_scheduler_cls.return_value = MagicMock()
            mock_ts_cls.return_value = MagicMock()

            container.configure(binder)

            # Verify all bind calls were made
            assert binder.bind.call_count >= 20

    def test_configure_binds_beanie_initializer_with_settings(self):
        """Test that configure binds BeanieInitializer with correct settings."""
        settings = MagicMock(spec=Settings)
        settings.MONGO_URI = "mongodb://localhost:27017"
        settings.MONGO_DB = "test-db"
        settings.REDIS_URI = "redis://localhost:6379"
        settings.DEBUG = False
        settings.I18N_PATH = "../shared/i18n"

        container = ServicesContainer(settings)
        binder = MagicMock(spec=Binder)

        with patch("app.services.container.BeanieInitializer") as mock_beanie_cls:
            mock_beanie = MagicMock()
            mock_beanie_cls.return_value = mock_beanie
            container.configure(binder)

            # Check BeanieInitializer was instantiated with correct args
            mock_beanie_cls.assert_called_once_with(
                mongo_uri="mongodb://localhost:27017",
                db_name="test-db",
            )

    def test_configure_binds_events_service_config(self):
        """Test that configure binds EventsServiceConfig with correct params."""
        settings = MagicMock(spec=Settings)
        settings.MONGO_URI = "mongodb://localhost:27017"
        settings.MONGO_DB = "test-db"
        settings.REDIS_URI = "redis://localhost:6379"
        settings.DEBUG = False
        settings.I18N_PATH = "../shared/i18n"

        container = ServicesContainer(settings)
        binder = MagicMock(spec=Binder)

        with patch("app.services.container.BeanieInitializer"), \
             patch("app.services.container.EventsServiceConfig") as mock_config_cls:
            mock_config = MagicMock()
            mock_config_cls.return_value = mock_config

            container.configure(binder)

            mock_config_cls.assert_called_once_with("redis://localhost:6379", False)

    def test_configure_binds_events_service(self):
        """Test that configure binds EventsService with config instance."""
        settings = MagicMock(spec=Settings)
        settings.MONGO_URI = "mongodb://localhost:27017"
        settings.MONGO_DB = "test-db"
        settings.REDIS_URI = "redis://localhost:6379"
        settings.DEBUG = False
        settings.I18N_PATH = "../shared/i18n"

        container = ServicesContainer(settings)
        binder = MagicMock(spec=Binder)

        with patch("app.services.container.BeanieInitializer"), \
             patch("app.services.container.EventsServiceConfig") as mock_config_cls, \
             patch("app.services.container.EventsService") as mock_events_cls:
            mock_config = MagicMock()
            mock_config_cls.return_value = mock_config
            mock_events = MagicMock()
            mock_events_cls.return_value = mock_events

            container.configure(binder)

            mock_events_cls.assert_called_once_with(mock_config)

    def test_configure_binds_scheduler(self):
        """Test that configure binds AsyncIOScheduler."""
        settings = MagicMock(spec=Settings)
        settings.MONGO_URI = "mongodb://localhost:27017"
        settings.MONGO_DB = "test-db"
        settings.REDIS_URI = "redis://localhost:6379"
        settings.DEBUG = False
        settings.I18N_PATH = "../shared/i18n"

        container = ServicesContainer(settings)
        binder = MagicMock(spec=Binder)

        with patch("app.services.container.BeanieInitializer"), \
             patch("app.services.container.AsyncIOScheduler") as mock_scheduler_cls:
            mock_scheduler = MagicMock()
            mock_scheduler_cls.return_value = mock_scheduler

            container.configure(binder)

            mock_scheduler_cls.assert_called_once()

    def test_configure_binds_translation_service(self):
        """Test that configure binds TranslationService with correct path."""
        settings = MagicMock(spec=Settings)
        settings.MONGO_URI = "mongodb://localhost:27017"
        settings.MONGO_DB = "test-db"
        settings.REDIS_URI = "redis://localhost:6379"
        settings.DEBUG = False
        settings.I18N_PATH = "../shared/i18n"

        container = ServicesContainer(settings)
        binder = MagicMock(spec=Binder)

        with patch("app.services.container.BeanieInitializer"), \
             patch("app.services.container.TranslationService") as mock_ts_cls:
            mock_ts = MagicMock()
            mock_ts_cls.return_value = mock_ts

            container.configure(binder)

            mock_ts_cls.assert_called_once_with(path="../shared/i18n")

    def test_configure_binds_stations_service_with_noscope(self):
        """Test that configure binds StationsService with noscope."""
        settings = MagicMock(spec=Settings)
        settings.MONGO_URI = "mongodb://localhost:27017"
        settings.MONGO_DB = "test-db"
        settings.REDIS_URI = "redis://localhost:6379"
        settings.DEBUG = False
        settings.I18N_PATH = "../shared/i18n"

        container = ServicesContainer(settings)
        binder = MagicMock(spec=Binder)

        with patch("app.services.container.BeanieInitializer"):
            container.configure(binder)

            from app.services.stations import StationsService
            binder.bind.assert_any_call(StationsService, scope=noscope)

    def test_configure_binds_ext_device_service(self):
        """Test that configure binds IExtDeviceService to ExtDeviceService."""
        settings = MagicMock(spec=Settings)
        settings.MONGO_URI = "mongodb://localhost:27017"
        settings.MONGO_DB = "test-db"
        settings.REDIS_URI = "redis://localhost:6379"
        settings.DEBUG = False
        settings.I18N_PATH = "../shared/i18n"

        container = ServicesContainer(settings)
        binder = MagicMock(spec=Binder)

        with patch("app.services.container.BeanieInitializer"):
            container.configure(binder)

            from app.services.interfaces import IExtDeviceService
            from app.services.ext_device import ExtDeviceService
            binder.bind.assert_any_call(IExtDeviceService, to=ExtDeviceService)

    def test_configure_binds_message_generator_service(self):
        """Test that configure binds IMessageGeneratorService to MessageGeneratorService."""
        settings = MagicMock(spec=Settings)
        settings.MONGO_URI = "mongodb://localhost:27017"
        settings.MONGO_DB = "test-db"
        settings.REDIS_URI = "redis://localhost:6379"
        settings.DEBUG = False
        settings.I18N_PATH = "../shared/i18n"

        container = ServicesContainer(settings)
        binder = MagicMock(spec=Binder)

        with patch("app.services.container.BeanieInitializer"):
            container.configure(binder)

            from app.services.interfaces import IMessageGeneratorService
            from app.services.message_generator import MessageGeneratorService
            binder.bind.assert_any_call(IMessageGeneratorService, to=MessageGeneratorService, scope=noscope)
