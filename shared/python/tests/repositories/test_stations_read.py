"""Tests for shared/repositories/implementations/stations_read.py."""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from beanie import PydanticObjectId

from shared.repositories.implementations.stations_read import StationsReadRepository
from shared.models.station import Station


# Mock Beanie class-level query attributes
Station.order = MagicMock()
Station.id = MagicMock()
Station.station_id = MagicMock()


class TestStationsReadRepository:
    """Tests for StationsReadRepository."""

    @pytest.mark.asyncio
    async def test_get_stations_all(self):
        """Test get_stations with all=True."""
        mock_stations = [MagicMock(spec=Station)]
        with patch.object(Station, 'find') as mock_find:
            mock_find.return_value.sort.return_value.to_list = AsyncMock(return_value=mock_stations)
            repo = StationsReadRepository()
            result = await repo.get_stations(all=True)
            assert result == mock_stations
            mock_find.assert_called_once_with({})

    @pytest.mark.asyncio
    async def test_get_stations_enabled_only(self):
        """Test get_stations with all=False (enabled only)."""
        mock_stations = [MagicMock(spec=Station)]
        with patch.object(Station, 'find') as mock_find:
            mock_find.return_value.sort.return_value.to_list = AsyncMock(return_value=mock_stations)
            repo = StationsReadRepository()
            result = await repo.get_stations(all=False)
            assert result == mock_stations
            mock_find.assert_called_once_with({"enabled": True})

    @pytest.mark.asyncio
    async def test_get_station_found(self):
        """Test get_station when found."""
        station_id = str(PydanticObjectId("507f1f77bcf86cd799439011"))
        mock_station = MagicMock(spec=Station)
        with patch.object(Station, 'find_one', new_callable=AsyncMock) as mock_find_one:
            mock_find_one.return_value = mock_station
            repo = StationsReadRepository()
            result = await repo.get_station(station_id)
            assert result == mock_station

    @pytest.mark.asyncio
    async def test_get_station_not_found(self):
        """Test get_station when not found."""
        station_id = str(PydanticObjectId("507f1f77bcf86cd799439011"))
        with patch.object(Station, 'find_one', new_callable=AsyncMock) as mock_find_one:
            mock_find_one.return_value = None
            repo = StationsReadRepository()
            result = await repo.get_station(station_id)
            assert result is None

    @pytest.mark.asyncio
    async def test_get_station_by_station_id(self):
        """Test get_station_by_station_id."""
        mock_station = MagicMock(spec=Station)
        with patch.object(Station, 'find_one', new_callable=AsyncMock) as mock_find_one:
            mock_find_one.return_value = mock_station
            repo = StationsReadRepository()
            result = await repo.get_station_by_station_id(123)
            assert result == mock_station