"""Tests for sse-back-end/app/main.py."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI

from app.main import lifespan, create_app, make_shutdown_handler
from app.settings import Settings


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
    async def test_lifespan_starts_metrics_server(self):
        """Test that lifespan starts the metrics server on port 9098."""
        app = FastAPI()
        mock_events = MagicMock()
        mock_events.start = AsyncMock()
        mock_events.shutdown = AsyncMock()
        app.state.events = mock_events

        with patch("app.main.register_chained_signal_handlers") as mock_register_signals, \
             patch("app.main.metrics_server_lifespan") as mock_metrics_lifespan:

            mock_metrics_cm = AsyncMock()
            mock_metrics_cm.__aenter__ = AsyncMock()
            mock_metrics_cm.__aexit__ = AsyncMock()
            mock_metrics_lifespan.return_value = mock_metrics_cm

            async with lifespan(app):
                pass

            mock_events.start.assert_called_once()
            mock_events.shutdown.assert_called_once()
            mock_register_signals.assert_called_once()
            
            # Verify metrics_server_lifespan was called with correct port
            mock_metrics_lifespan.assert_called_once_with(host="0.0.0.0", port=9098)
            mock_metrics_cm.__aenter__.assert_called_once()
            mock_metrics_cm.__aexit__.assert_called_once()


class TestCreateApp:
    @pytest.mark.asyncio
    async def test_create_app_sets_lifespan(self):
        """Test that create_app sets the lifespan with metrics server."""
        settings = MagicMock(spec=Settings)
        settings.DEBUG = False
        settings.REDIS_URI = "redis://localhost:6379"

        with patch("app.main.create_injector") as mock_create_injector, \
             patch("app.main.set_injector") as mock_set_injector, \
             patch("app.main.EventsService") as mock_events_cls, \
             patch("app.main.register_routes") as mock_register_routes, \
             patch("app.main.get_version", return_value="1.0.0"):

            mock_injector = MagicMock()
            mock_create_injector.return_value = mock_injector

            mock_events = MagicMock()
            mock_events_cls.return_value = mock_events

            app = create_app(settings)

            assert app.router.lifespan_context is not None
            mock_create_injector.assert_called_once_with(settings)
            mock_set_injector.assert_called_once()
            mock_events_cls.assert_called_once()
            mock_register_routes.assert_called_once()