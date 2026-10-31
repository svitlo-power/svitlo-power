"""Tests for app lifespan."""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.lifespan import lifespan
from shared.services.settings.service import SettingsService


class TestLifespan:
    @pytest.mark.asyncio
    async def test_lifespan_startup_shutdown(self):
        """Test lifespan startup and shutdown."""
        mock_app = MagicMock(spec=FastAPI)
        mock_app.state = MagicMock()
        mock_beanie_initializer = AsyncMock()
        mock_beanie_initializer._client = AsyncMock()
        mock_aiohttp_session = AsyncMock()
        mock_redis_client = AsyncMock()
        mock_settings_service = AsyncMock()

        # Configure the injector.get to return different mocks based on what's requested
        def injector_get_side_effect(cls):
            if cls.__name__ == 'BeanieInitializer':
                return mock_beanie_initializer
            elif cls.__name__ == 'ClientSession':
                return mock_aiohttp_session
            elif cls.__name__ == 'Redis':
                return mock_redis_client
            elif cls.__name__ == 'SettingsService':
                return mock_settings_service
            return MagicMock()

        mock_app.state.injector.get.side_effect = injector_get_side_effect

        with patch('app.lifespan.set_settings_service') as mock_set_settings:
            async with lifespan(mock_app):
                # Startup should have been called
                mock_beanie_initializer.init.assert_called_once()

                # Resources should be stored in app.state
                assert mock_app.state.mongo_client == mock_beanie_initializer._client
                assert mock_app.state.aiohttp_session == mock_aiohttp_session
                assert mock_app.state.redis_client == mock_redis_client

                # Settings service should be retrieved and set
                mock_app.state.injector.get.assert_any_call(SettingsService)
                mock_set_settings.assert_called_once_with(mock_settings_service)

            # After exiting context, shutdown should close resources
            mock_aiohttp_session.close.assert_called_once()
            mock_redis_client.close.assert_called_once()
            mock_beanie_initializer._client.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_lifespan_with_exception(self):
        """Test lifespan handles exceptions during startup."""
        mock_app = MagicMock(spec=FastAPI)
        mock_app.state = MagicMock()
        mock_beanie_initializer = AsyncMock()
        mock_beanie_initializer.init.side_effect = Exception("Connection failed")
        mock_app.state.injector.get.return_value = mock_beanie_initializer

        with pytest.raises(Exception, match="Connection failed"):
            async with lifespan(mock_app):
                pass

        mock_beanie_initializer.init.assert_called_once()

    @pytest.mark.asyncio
    async def test_lifespan_shutdown_handles_missing_resources(self):
        """Test lifespan shutdown handles missing resources gracefully."""
        mock_app = MagicMock(spec=FastAPI)
        mock_app.state = MagicMock()
        mock_beanie_initializer = AsyncMock()
        mock_beanie_initializer._client = AsyncMock()
        mock_aiohttp_session = AsyncMock()
        mock_redis_client = AsyncMock()
        mock_settings_service = AsyncMock()

        def injector_get_side_effect(cls):
            if cls.__name__ == 'BeanieInitializer':
                return mock_beanie_initializer
            elif cls.__name__ == 'ClientSession':
                return mock_aiohttp_session
            elif cls.__name__ == 'Redis':
                return mock_redis_client
            elif cls.__name__ == 'SettingsService':
                return mock_settings_service
            return MagicMock()

        mock_app.state.injector.get.side_effect = injector_get_side_effect

        with patch('app.lifespan.set_settings_service'):
            async with lifespan(mock_app):
                pass

            # All close methods should be called
            mock_aiohttp_session.close.assert_called_once()
            mock_redis_client.close.assert_called_once()
            mock_beanie_initializer._client.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_lifespan_shutdown_handles_none_resources(self):
        """Test lifespan shutdown handles None resources gracefully."""
        mock_app = MagicMock(spec=FastAPI)
        mock_app.state = MagicMock()
        mock_beanie_initializer = AsyncMock()
        mock_beanie_initializer._client = None
        mock_aiohttp_session = None
        mock_redis_client = None
        mock_settings_service = AsyncMock()

        def injector_get_side_effect(cls):
            if cls.__name__ == 'BeanieInitializer':
                return mock_beanie_initializer
            elif cls.__name__ == 'ClientSession':
                return mock_aiohttp_session
            elif cls.__name__ == 'Redis':
                return mock_redis_client
            elif cls.__name__ == 'SettingsService':
                return mock_settings_service
            return MagicMock()

        mock_app.state.injector.get.side_effect = injector_get_side_effect

        with patch('app.lifespan.set_settings_service'):
            async with lifespan(mock_app):
                pass

            # Should not raise any exceptions
            # close should not be called on None
            mock_aiohttp_session.close.assert_not_called() if mock_aiohttp_session else None
            mock_redis_client.close.assert_not_called() if mock_redis_client else None
            mock_beanie_initializer._client.close.assert_not_called() if mock_beanie_initializer._client else None

    @pytest.mark.asyncio
    async def test_lifespan_starts_metrics_server(self):
        """Test that lifespan starts the metrics server on port 9097."""
        mock_app = MagicMock(spec=FastAPI)
        mock_app.state = MagicMock()
        mock_beanie_initializer = AsyncMock()
        mock_beanie_initializer._client = AsyncMock()
        mock_aiohttp_session = AsyncMock()
        mock_redis_client = AsyncMock()
        mock_settings_service = AsyncMock()

        def injector_get_side_effect(cls):
            if cls.__name__ == 'BeanieInitializer':
                return mock_beanie_initializer
            elif cls.__name__ == 'ClientSession':
                return mock_aiohttp_session
            elif cls.__name__ == 'Redis':
                return mock_redis_client
            elif cls.__name__ == 'SettingsService':
                return mock_settings_service
            return MagicMock()

        mock_app.state.injector.get.side_effect = injector_get_side_effect

        with patch('app.lifespan.set_settings_service'), \
             patch('app.lifespan.metrics_server_lifespan') as mock_metrics_lifespan:

            mock_metrics_cm = AsyncMock()
            mock_metrics_cm.__aenter__ = AsyncMock()
            mock_metrics_cm.__aexit__ = AsyncMock()
            mock_metrics_lifespan.return_value = mock_metrics_cm

            async with lifespan(mock_app):
                pass

            # Verify metrics_server_lifespan was called with correct port
            mock_metrics_lifespan.assert_called_once_with(host="0.0.0.0", port=9097)
            mock_metrics_cm.__aenter__.assert_called_once()
            mock_metrics_cm.__aexit__.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])