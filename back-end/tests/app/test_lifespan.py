"""Tests for app/lifespan.py."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI

from app.lifespan import lifespan, create_user, setup_bots, make_shutdown_handler
from app.settings import Settings


class TestCreateUser:
    @pytest.mark.asyncio
    async def test_create_user_with_admin_user(self):
        settings = MagicMock(spec=Settings)
        settings.ADMIN_USER = "admin"
        settings.ADMIN_PASSWORD = "password"

        injector = MagicMock()
        mock_auth = MagicMock()
        mock_auth.add_user = AsyncMock()
        injector.get = MagicMock(return_value=mock_auth)

        await create_user(settings, injector)
        mock_auth.add_user.assert_called_once_with("admin", "password")

    @pytest.mark.asyncio
    async def test_create_user_without_admin_user(self):
        settings = MagicMock(spec=Settings)
        settings.ADMIN_USER = None

        injector = MagicMock()

        await create_user(settings, injector)
        injector.get.assert_not_called()


class TestSetupBots:
    @pytest.mark.asyncio
    async def test_setup_bots_registers_enabled_bots(self):
        injector = MagicMock()
        mock_bots_service = MagicMock()
        mock_bots_service.get_enabled_bots = AsyncMock(return_value=[])
        mock_telegram_service = MagicMock()
        mock_telegram_service.add_bot = AsyncMock()

        injector.get = MagicMock(side_effect=[mock_bots_service, mock_telegram_service])

        await setup_bots(injector)
        mock_bots_service.get_enabled_bots.assert_called_once()
        mock_telegram_service.add_bot.assert_not_called()


class TestMakeShutdownHandler:
    @pytest.mark.asyncio
    async def test_shutdown_requests_shutdown(self):
        mock_events = MagicMock()
        mock_events.request_shutdown = AsyncMock()

        handler = await make_shutdown_handler(mock_events)
        await handler(15)
        mock_events.request_shutdown.assert_called_once()


class TestLifespan:
    @pytest.mark.asyncio
    async def test_lifespan_yields(self):
        app = FastAPI()
        settings = MagicMock(spec=Settings)
        settings.DEBUG = False
        settings.STATISTIC_KEEP_DAYS = 3
        settings.SSE_PING_INTERVAL = 45
        settings.DEYE_FETCH_INTERVAL = 120
        settings.DEYE_SYNC_STATIONS_ON_POLL = False
        settings.DEYE_BASE_URL = None
        settings.DEYE_APP_ID = None
        settings.DEYE_APP_SECRET = None
        settings.DEYE_EMAIL = None
        settings.DEYE_PASSWORD = None
        settings.TG_HOOK_BASE_URL = None
        settings.ADMIN_USER = None
        settings.ADMIN_PASSWORD = None
        settings.BOT_TIMEZONE = "utc"
        settings.MONGO_URI = "mongodb://localhost:27017"
        settings.MONGO_DB = "test-db"
        settings.REDIS_URI = "redis://localhost:6379"
        settings.I18N_PATH = "../shared/i18n"
        app.state.settings = settings

        with patch("app.lifespan.init_container") as mock_init_container, \
             patch("app.lifespan.bind_client_session") as mock_bind, \
             patch("app.lifespan.BeanieInitializer") as mock_beanie_cls, \
             patch("app.lifespan.StationConnectionsService") as mock_conn_cls, \
             patch("app.lifespan.TelegramService") as mock_tg_cls, \
             patch("app.lifespan.EventsService") as mock_events_cls, \
             patch("app.lifespan.AsyncIOScheduler") as mock_scheduler_cls, \
             patch("app.lifespan.register_jobs") as mock_register_jobs, \
             patch("app.lifespan.register_routes") as mock_register_routes, \
             patch("app.lifespan.setup_bots") as mock_setup_bots, \
             patch("app.lifespan.create_user") as mock_create_user, \
             patch("app.lifespan.register_chained_signal_handlers") as mock_register_signals:

            mock_injector = MagicMock()
            mock_init_container.return_value = mock_injector

            mock_beanie = MagicMock()
            mock_beanie.init = AsyncMock()

            mock_conn = MagicMock()
            mock_conn.init = AsyncMock()
            mock_conn.shutdown = AsyncMock()

            mock_tg = MagicMock()
            mock_tg.shutdown = AsyncMock()

            mock_scheduler = MagicMock()
            mock_scheduler.start = MagicMock()
            mock_scheduler.shutdown = MagicMock()

            mock_events = MagicMock()
            mock_events.start = AsyncMock()
            mock_events.shutdown = AsyncMock()

            mock_injector.get = MagicMock(side_effect=[
                mock_beanie,  # BeanieInitializer
                mock_conn,  # StationConnectionsService
                mock_tg,  # TelegramService
                mock_events,  # EventsService
                mock_scheduler,  # AsyncIOScheduler
            ])

            async with lifespan(app):
                pass

            mock_init_container.assert_called_once()
            mock_bind.assert_called_once()
            mock_register_jobs.assert_called_once()
            mock_register_routes.assert_called_once()
            mock_setup_bots.assert_called_once()
            mock_create_user.assert_called_once()
            mock_register_signals.assert_called_once()
