"""Tests for app container."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import aiohttp
import redis.asyncio as redis

from app.container import AppModule, BeanieInitializer
from app.settings import Settings
from shared.repositories.interfaces import (
    IDashboardReadRepository,
    IExtDataReadRepository,
    IStationsReadRepository,
    IStationsDataReadRepository,
    IUsersReadRepository,
    IOutagesScheduleRepository,
    IPushDevicesRepository,
    IPushTopicsRepository,
)
from shared.services import EventsService, SettingsService
from shared.services.events import EventsServiceConfig
from shared.models import SystemSetting


class TestBeanieInitializer:
    @pytest.mark.asyncio
    async def test_init(self):
        with patch('app.container.AsyncMongoClient') as mock_client_class, \
             patch('app.container.init_beanie') as mock_init_beanie:
            
            mock_client = AsyncMock()
            mock_client_class.return_value = mock_client
            
            initializer = BeanieInitializer("mongodb://localhost:27017", "test-db")
            await initializer.init()
            
            mock_client_class.assert_called_once_with("mongodb://localhost:27017")
            mock_init_beanie.assert_called_once()
            call_args = mock_init_beanie.call_args
            assert call_args.kwargs['database'] == mock_client['test-db']
            assert 'document_models' in call_args.kwargs
            document_models = call_args.kwargs['document_models']
            assert SystemSetting in document_models


class TestAppModule:
    @pytest.fixture
    def mock_settings(self):
        settings = MagicMock(spec=Settings)
        settings.MONGO_URI = "mongodb://localhost:27017"
        settings.MONGO_DB = "test-db"
        settings.REDIS_URI = "redis://localhost:6379/0"
        settings.DEBUG = True
        return settings

    def test_provide_settings(self, mock_settings):
        module = AppModule()
        with patch('app.container.get_settings') as mock_get_settings:
            mock_get_settings.return_value = mock_settings
            
            result = module.provide_settings()
            
            mock_get_settings.assert_called_once()
            assert result == mock_settings

    def test_provide_beanie_initializer(self, mock_settings):
        module = AppModule()
        with patch('app.container.BeanieInitializer') as mock_initializer_class:
            mock_initializer = MagicMock()
            mock_initializer_class.return_value = mock_initializer
            
            result = module.provide_beanie_initializer(mock_settings)
            
            mock_initializer_class.assert_called_once_with(
                str(mock_settings.MONGO_URI), 
                mock_settings.MONGO_DB
            )
            assert result == mock_initializer

    def test_provide_redis_client(self, mock_settings):
        module = AppModule()
        with patch('app.container.redis.Redis.from_url') as mock_from_url:
            mock_redis = MagicMock()
            mock_from_url.return_value = mock_redis
            
            result = module.provide_redis_client(mock_settings)
            
            mock_from_url.assert_called_once_with(
                str(mock_settings.REDIS_URI), 
                decode_responses=True
            )
            assert result == mock_redis

    def test_provide_events_config(self, mock_settings):
        module = AppModule()
        with patch('app.container.EventsServiceConfig') as mock_config_class:
            mock_config = MagicMock()
            mock_config_class.return_value = mock_config
            
            result = module.provide_events_config(mock_settings)
            
            mock_config_class.assert_called_once_with(
                str(mock_settings.REDIS_URI), 
                mock_settings.DEBUG
            )
            assert result == mock_config

    def test_provide_events_service(self):
        module = AppModule()
        mock_config = MagicMock(spec=EventsServiceConfig)
        with patch('app.container.EventsService') as mock_service_class:
            mock_service = MagicMock()
            mock_service_class.return_value = mock_service
            
            result = module.provide_events_service(mock_config)
            
            mock_service_class.assert_called_once_with(mock_config)
            assert result == mock_service

    def test_provide_aiohttp_session(self):
        module = AppModule()
        with patch('app.container.aiohttp.ClientSession') as mock_session_class:
            mock_session = MagicMock()
            mock_session_class.return_value = mock_session
            
            result = module.provide_aiohttp_session()
            
            mock_session_class.assert_called_once()
            assert result == mock_session

    def test_provide_dashboard_repository(self):
        module = AppModule()
        with patch('app.container.DashboardReadRepository') as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo_class.return_value = mock_repo
            
            result = module.provide_dashboard_repository()
            
            mock_repo_class.assert_called_once()
            assert result == mock_repo

    def test_provide_ext_data_repository(self):
        module = AppModule()
        with patch('app.container.ExtDataReadRepository') as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo_class.return_value = mock_repo
            
            result = module.provide_ext_data_repository()
            
            mock_repo_class.assert_called_once()
            assert result == mock_repo

    def test_provide_stations_repository(self):
        module = AppModule()
        with patch('app.container.StationsReadRepository') as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo_class.return_value = mock_repo
            
            result = module.provide_stations_repository()
            
            mock_repo_class.assert_called_once()
            assert result == mock_repo

    def test_provide_stations_data_repository(self, mock_settings):
        module = AppModule()
        with patch('app.container.StationsDataReadRepository') as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo_class.return_value = mock_repo
            
            result = module.provide_stations_data_repository(mock_settings)
            
            mock_repo_class.assert_called_once_with(mock_settings)
            assert result == mock_repo

    def test_provide_users_repository(self):
        module = AppModule()
        with patch('app.container.UsersReadRepository') as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo_class.return_value = mock_repo
            
            result = module.provide_users_repository()
            
            mock_repo_class.assert_called_once()
            assert result == mock_repo

    def test_provide_outages_schedule_repository_debug(self, mock_settings):
        mock_settings.DEBUG = True
        module = AppModule()
        with patch('app.container.InMemoryOutagesScheduleRepository') as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo_class.return_value = mock_repo
            
            result = module.provide_outages_schedule_repository(mock_settings)
            
            mock_repo_class.assert_called_once()
            assert result == mock_repo

    def test_provide_outages_schedule_repository_production(self, mock_settings):
        mock_settings.DEBUG = False
        module = AppModule()
        with patch('app.container.RedisOutagesScheduleRepository', autospec=True) as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo_class.return_value = mock_repo
            
            result = module.provide_outages_schedule_repository(mock_settings)
            
            mock_repo_class.assert_called_once_with(str(mock_settings.REDIS_URI))
            assert result == mock_repo

    def test_provide_dashboard_service(self):
        module = AppModule()
        mock_events = MagicMock(spec=EventsService)
        mock_dashboard = MagicMock(spec=IDashboardReadRepository)
        mock_ext_data = MagicMock(spec=IExtDataReadRepository)
        mock_stations = MagicMock(spec=IStationsReadRepository)
        mock_stations_data = MagicMock(spec=IStationsDataReadRepository)
        mock_users = MagicMock(spec=IUsersReadRepository)
        mock_settings = MagicMock(spec=SettingsService)
        
        with patch('app.container.ReadOnlyDashboardService') as mock_service_class:
                mock_service = MagicMock()
                mock_service_class.return_value = mock_service
            
                result = module.provide_dashboard_service(
                    mock_events, mock_dashboard, mock_ext_data,
                    mock_stations, mock_stations_data, mock_users,
                    mock_settings
                )
            
                mock_service_class.assert_called_once_with(
                    events=mock_events,
                    dashboard=mock_dashboard,
                    ext_data=mock_ext_data,
                    stations=mock_stations,
                    stations_data=mock_stations_data,
                    users=mock_users,
                    settings=mock_settings,
                )
                assert result == mock_service

    def test_provide_outages_schedule_service(self):
        module = AppModule()
        mock_events = MagicMock(spec=EventsService)
        mock_session = MagicMock(spec=aiohttp.ClientSession)
        mock_repository = MagicMock(spec=IOutagesScheduleRepository)
        
        with patch('app.container.OutagesScheduleService') as mock_service_class:
            mock_service = MagicMock()
            mock_service_class.return_value = mock_service
            
            result = module.provide_outages_schedule_service(
                mock_events, mock_session, mock_repository
            )
            
            mock_service_class.assert_called_once_with(
                events=mock_events,
                session=mock_session,
                repository=mock_repository,
            )
            assert result == mock_service


    def test_provide_push_devices_repository(self):
        module = AppModule()
        with patch('app.container.PushDevicesRepository') as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo_class.return_value = mock_repo

            result = module.provide_push_devices_repository()

            mock_repo_class.assert_called_once()
            assert result == mock_repo

    def test_provide_push_topics_repository(self):
        module = AppModule()
        with patch('app.container.PushTopicsRepository') as mock_repo_class:
            mock_repo = MagicMock()
            mock_repo_class.return_value = mock_repo

            result = module.provide_push_topics_repository()

            mock_repo_class.assert_called_once()
            assert result == mock_repo

    def test_provide_push_devices_service(self):
        module = AppModule()
        mock_devices = MagicMock(spec=IPushDevicesRepository)
        mock_topics = MagicMock(spec=IPushTopicsRepository)

        with patch('app.container.PushDevicesService') as mock_service_class:
            mock_service = MagicMock()
            mock_service_class.return_value = mock_service

            result = module.provide_push_devices_service(mock_devices, mock_topics)

            mock_service_class.assert_called_once_with(devices=mock_devices, topics=mock_topics)
            assert result == mock_service

if __name__ == "__main__":
    pytest.main([__file__, "-v"])