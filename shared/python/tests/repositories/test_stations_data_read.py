"""Tests for shared/repositories/implementations/stations_data_read.py."""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime, timezone
from beanie import PydanticObjectId

from shared.repositories.implementations.stations_data_read import StationsDataReadRepository
from shared.models import StationData, AssumedStationStatus
from shared.settings.base import BaseDeyeAppSettings


# Mock Beanie class-level query attributes
StationData.station_id = MagicMock()
_lut_mock = MagicMock()
_lut_mock.__lt__ = MagicMock(return_value=MagicMock())
_lut_mock.__le__ = MagicMock(return_value=MagicMock())
_lut_mock.__gt__ = MagicMock(return_value=MagicMock())
_lut_mock.__ge__ = MagicMock(return_value=MagicMock())
StationData.last_update_time = _lut_mock


def make_repo():
    settings = MagicMock(spec=BaseDeyeAppSettings)
    settings.DEYE_REPORT_INTERVAL = 300
    settings.DEYE_ASSUMED_OFFLINE_REPORTS = 2
    return StationsDataReadRepository(settings), settings


class TestStationsDataReadRepository:
    """Tests for StationsDataReadRepository."""

    @pytest.mark.asyncio
    async def test_get_full_station_data_range(self):
        """Test get_full_station_data_range."""
        repo, _ = make_repo()
        station_id = str(PydanticObjectId("507f1f77bcf86cd799439011"))
        start_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end_date = datetime(2024, 1, 31, tzinfo=timezone.utc)
        mock_stations = [MagicMock(spec=StationData)]
        
        with patch.object(StationData, 'find') as mock_find:
            mock_find.return_value.sort.return_value.to_list = AsyncMock(return_value=mock_stations)
            result = await repo.get_full_station_data_range(station_id, start_date, end_date)
            assert result == mock_stations

    @pytest.mark.asyncio
    async def test_get_full_station_data_range_exception(self):
        """Test get_full_station_data_range handles exception."""
        repo, _ = make_repo()
        station_id = str(PydanticObjectId("507f1f77bcf86cd799439011"))
        start_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end_date = datetime(2024, 1, 31, tzinfo=timezone.utc)
        
        with patch.object(StationData, 'find', side_effect=Exception("DB error")):
            result = await repo.get_full_station_data_range(station_id, start_date, end_date)
            assert result == []

    @pytest.mark.asyncio
    async def test_get_last_station_data(self):
        """Test get_last_station_data."""
        repo, _ = make_repo()
        station_id = PydanticObjectId("507f1f77bcf86cd799439011")
        mock_station = MagicMock(spec=StationData)
        
        with patch.object(StationData, 'find') as mock_find:
            mock_find.return_value.sort.return_value.first_or_none = AsyncMock(return_value=mock_station)
            result = await repo.get_last_station_data(station_id)
            assert result == mock_station

    @pytest.mark.asyncio
    async def test_get_station_data_average_column(self):
        """Test get_station_data_average_column."""
        repo, _ = make_repo()
        start_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end_date = datetime(2024, 1, 31, tzinfo=timezone.utc)
        station_id = 123
        column_name = "battery_power"
        
        with patch.object(StationData, 'aggregate') as mock_aggregate:
            mock_aggregate.return_value.to_list = AsyncMock(return_value=[{"avg_value": 150.0}])
            result = await repo.get_station_data_average_column(start_date, end_date, station_id, column_name)
            assert result == 150.0

    @pytest.mark.asyncio
    async def test_get_station_data_average_column_no_result(self):
        """Test get_station_data_average_column when no result."""
        repo, _ = make_repo()
        start_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end_date = datetime(2024, 1, 31, tzinfo=timezone.utc)
        station_id = 123
        column_name = "battery_power"
        
        with patch.object(StationData, 'aggregate') as mock_aggregate:
            mock_aggregate.return_value.to_list = AsyncMock(return_value=[])
            result = await repo.get_station_data_average_column(start_date, end_date, station_id, column_name)
            assert result == 0.0

    @pytest.mark.asyncio
    async def test_get_station_data_average_column_invalid_field(self):
        """Test get_station_data_average_column with invalid field."""
        repo, _ = make_repo()
        start_date = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end_date = datetime(2024, 1, 31, tzinfo=timezone.utc)
        station_id = 123
        column_name = "invalid_field"
        
        with pytest.raises(ValueError):
            await repo.get_station_data_average_column(start_date, end_date, station_id, column_name)

    @pytest.mark.asyncio
    async def test_get_assumed_connection_status_offline_no_data(self):
        """Test get_assumed_connection_status returns OFFLINE when no data."""
        repo, _ = make_repo()
        station_id = 123
        
        with patch.object(StationData, 'find') as mock_find:
            mock_find.return_value.sort.return_value.limit.return_value.to_list = AsyncMock(return_value=[])
            result = await repo.get_assumed_connection_status(station_id)
            assert result == AssumedStationStatus.OFFLINE

    @pytest.mark.asyncio
    async def test_get_assumed_connection_status_normal(self):
        """Test get_assumed_connection_status returns NORMAL when recent data."""
        repo, _ = make_repo()
        station_id = 123
        mock_station_data = MagicMock()
        mock_station_data.last_update_time = datetime.now(timezone.utc)
        
        with patch.object(StationData, 'find') as mock_find:
            mock_find.return_value.sort.return_value.limit.return_value.to_list = AsyncMock(return_value=[mock_station_data])
            result = await repo.get_assumed_connection_status(station_id)
            assert result == AssumedStationStatus.NORMAL

    @pytest.mark.asyncio
    async def test_get_assumed_connection_status_offline(self):
        """Test get_assumed_connection_status returns OFFLINE when data is old."""
        repo, settings = make_repo()
        station_id = 123
        old_time = datetime.now(timezone.utc).replace(year=2020)
        mock_station_data = MagicMock()
        mock_station_data.last_update_time = old_time
        
        with patch.object(StationData, 'find') as mock_find:
            mock_find.return_value.sort.return_value.limit.return_value.to_list = AsyncMock(return_value=[mock_station_data])
            result = await repo.get_assumed_connection_status(station_id)
            assert result == AssumedStationStatus.OFFLINE