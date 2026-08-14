"""Tests for app/services/maintenance/service.py."""
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.services.maintenance.service import MaintenanceService


class TestMaintenanceService:
    @pytest.mark.asyncio
    async def test_delete_old_data_calls_both_repositories(self):
        mock_stations_data = MagicMock()
        mock_stations_data.delete_old_data = AsyncMock()
        mock_ext_data = MagicMock()
        mock_ext_data.delete_old_data = AsyncMock()

        service = MaintenanceService(mock_stations_data, mock_ext_data)
        await service.delete_old_data(7)

        mock_stations_data.delete_old_data.assert_called_once_with(7)
        mock_ext_data.delete_old_data.assert_called_once_with(7)

    @pytest.mark.asyncio
    async def test_delete_old_data_with_zero_days(self):
        mock_stations_data = MagicMock()
        mock_stations_data.delete_old_data = AsyncMock()
        mock_ext_data = MagicMock()
        mock_ext_data.delete_old_data = AsyncMock()

        service = MaintenanceService(mock_stations_data, mock_ext_data)
        await service.delete_old_data(0)

        mock_stations_data.delete_old_data.assert_called_once_with(0)
        mock_ext_data.delete_old_data.assert_called_once_with(0)
