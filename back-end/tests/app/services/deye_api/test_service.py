"""Tests for app/services/deye_api/service.py."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.deye_api.service import DeyeApiService
from app.services.deye_api.models import DeyeConfig
from app.models.deye import DeyeStationList, DeyeStationData


class TestDeyeApiService:
    def test_init_creates_client_with_config(self):
        config = DeyeConfig(
            base_url="https://api.example.com",
            app_id="app123",
            app_secret="secret",
            email="test@example.com",
            password="password",
        )
        service = DeyeApiService(config)
        assert service._client is not None
        assert service._client._creds.base_url == "https://api.example.com"

    @pytest.mark.asyncio
    async def test_init_calls_client_init(self):
        config = DeyeConfig(
            base_url="https://api.example.com",
            app_id="app123",
            app_secret="secret",
            email="test@example.com",
            password="password",
        )
        service = DeyeApiService(config)
        service._client.init = AsyncMock()
        await service.init()
        service._client.init.assert_called_once()

    @pytest.mark.asyncio
    async def test_shutdown_calls_client_shutdown(self):
        config = DeyeConfig(
            base_url="https://api.example.com",
            app_id="app123",
            app_secret="secret",
            email="test@example.com",
            password="password",
        )
        service = DeyeApiService(config)
        service._client.shutdown = AsyncMock()
        await service.shutdown()
        service._client.shutdown.assert_called_once()

    @pytest.mark.asyncio
    async def test_refresh_token_calls_client_refresh(self):
        config = DeyeConfig(
            base_url="https://api.example.com",
            app_id="app123",
            app_secret="secret",
            email="test@example.com",
            password="password",
        )
        service = DeyeApiService(config)
        service._client.refresh_token = AsyncMock()
        await service.refresh_token()
        service._client.refresh_token.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_station_list_success(self):
        config = DeyeConfig(
            base_url="https://api.example.com",
            app_id="app123",
            app_secret="secret",
            email="test@example.com",
            password="password",
        )
        service = DeyeApiService(config)
        mock_data = {
            "code": "0",
            "msg": "success",
            "requestId": "req-123",
            "success": True,
            "total": 1,
            "stationList": [{"id": 1, "name": "Test Station"}],
        }
        service._client.get_station_list = AsyncMock(return_value=mock_data)

        result = await service.get_station_list()
        assert isinstance(result, DeyeStationList)
        assert result.success is True
        assert len(result.station_list) == 1

    @pytest.mark.asyncio
    async def test_get_station_list_failure_returns_none(self):
        config = DeyeConfig(
            base_url="https://api.example.com",
            app_id="app123",
            app_secret="secret",
            email="test@example.com",
            password="password",
        )
        service = DeyeApiService(config)
        service._client.get_station_list = AsyncMock(return_value=None)

        result = await service.get_station_list()
        assert result is None

    @pytest.mark.asyncio
    async def test_get_station_list_api_error_returns_none(self):
        config = DeyeConfig(
            base_url="https://api.example.com",
            app_id="app123",
            app_secret="secret",
            email="test@example.com",
            password="password",
        )
        service = DeyeApiService(config)
        mock_data = {"code": "1", "msg": "error", "success": False}
        service._client.get_station_list = AsyncMock(return_value=mock_data)

        result = await service.get_station_list()
        assert result is None

    @pytest.mark.asyncio
    async def test_get_station_data_success(self):
        config = DeyeConfig(
            base_url="https://api.example.com",
            app_id="app123",
            app_secret="secret",
            email="test@example.com",
            password="password",
        )
        service = DeyeApiService(config)
        mock_data = {
            "code": "0",
            "msg": "success",
            "requestId": "req-123",
            "success": True,
            "lastUpdateTime": 1234567890.0,
            "batteryPower": 100.0,
            "batterySOC": 85.0,
        }
        service._client.get_station_data = AsyncMock(return_value=mock_data)

        result = await service.get_station_data(1)
        assert isinstance(result, DeyeStationData)
        assert result.success is True
        assert result.battery_power == 100.0

    @pytest.mark.asyncio
    async def test_get_station_data_failure_returns_none(self):
        config = DeyeConfig(
            base_url="https://api.example.com",
            app_id="app123",
            app_secret="secret",
            email="test@example.com",
            password="password",
        )
        service = DeyeApiService(config)
        service._client.get_station_data = AsyncMock(return_value=None)

        result = await service.get_station_data(1)
        assert result is None
