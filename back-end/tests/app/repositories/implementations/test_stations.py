"""Tests for app/repositories/implementations/stations.py."""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime, timezone
from beanie import PydanticObjectId

from app.repositories.implementations.stations import StationsRepository
from shared.models.station import Station
from app.models.deye import DeyeStation

# Mock Beanie class-level query attributes
Station.order = MagicMock()
Station.id = MagicMock()
Station.station_id = MagicMock()
Station.connection_id = MagicMock()


class TestStationsRepository:
    """Tests for StationsRepository."""

    @pytest.mark.asyncio
    async def test_get_stations_all(self):
        """Test get_stations with all=True."""
        mock_stations = [MagicMock(spec=Station)]
        with patch.object(Station, 'find') as mock_find:
            mock_find.return_value.sort.return_value.to_list = AsyncMock(return_value=mock_stations)
            repo = StationsRepository()
            result = await repo.get_stations(all=True)
            assert result == mock_stations
            mock_find.assert_called_once_with({})

    @pytest.mark.asyncio
    async def test_get_stations_enabled_only(self):
        """Test get_stations with all=False (enabled only)."""
        mock_stations = [MagicMock(spec=Station)]
        with patch.object(Station, 'find') as mock_find:
            mock_find.return_value.sort.return_value.to_list = AsyncMock(return_value=mock_stations)
            repo = StationsRepository()
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
            repo = StationsRepository()
            result = await repo.get_station(station_id)
            assert result == mock_station

    @pytest.mark.asyncio
    async def test_get_station_not_found(self):
        """Test get_station when not found."""
        station_id = str(PydanticObjectId("507f1f77bcf86cd799439011"))
        with patch.object(Station, 'find_one', new_callable=AsyncMock) as mock_find_one:
            mock_find_one.return_value = None
            repo = StationsRepository()
            result = await repo.get_station(station_id)
            assert result is None

    @pytest.mark.asyncio
    async def test_get_station_by_station_id(self):
        """Test get_station_by_station_id."""
        mock_station = MagicMock(spec=Station)
        with patch.object(Station, 'find_one', new_callable=AsyncMock) as mock_find_one:
            mock_find_one.return_value = mock_station
            repo = StationsRepository()
            result = await repo.get_station_by_station_id(123)
            assert result == mock_station

    @pytest.mark.asyncio
    async def test_edit_station_found(self):
        """Test edit_station when station found."""
        station_id = str(PydanticObjectId("507f1f77bcf86cd799439011"))
        mock_station = MagicMock(spec=Station)
        mock_station.save = AsyncMock()
        repo = StationsRepository()
        with patch.object(repo, 'get_station', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_station
            await repo.edit_station(station_id, True, 1, 10.0, "alias")
            assert mock_station.enabled is True
            assert mock_station.order == 1
            assert mock_station.battery_capacity == 10.0
            assert mock_station.station_alias == "alias"
            mock_station.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_edit_station_not_found(self):
        """Test edit_station raises ValueError when not found."""
        station_id = str(PydanticObjectId("507f1f77bcf86cd799439011"))
        repo = StationsRepository()
        with patch.object(repo, 'get_station', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = None
            with pytest.raises(ValueError):
                await repo.edit_station(station_id, True, 1, 10.0, "alias")

    @pytest.mark.asyncio
    async def test_count_by_connection(self):
        """Test count_by_connection."""
        conn_id = PydanticObjectId("507f1f77bcf86cd799439011")
        with patch.object(Station, 'find') as mock_find:
            mock_find.return_value.count = AsyncMock(return_value=5)
            repo = StationsRepository()
            result = await repo.count_by_connection(conn_id)
            assert result == 5
            mock_find.assert_called_once()

    @pytest.mark.asyncio
    async def test_assign_connection_to_unassigned(self):
        """Test assign_connection_to_unassigned."""
        conn_id = PydanticObjectId("507f1f77bcf86cd799439011")
        with patch.object(Station, 'find') as mock_find:
            mock_find.return_value.update_many = AsyncMock()
            repo = StationsRepository()
            await repo.assign_connection_to_unassigned(conn_id)
            mock_find.assert_called_once_with({"connection_id": None})
            mock_find.return_value.update_many.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_station_new(self):
        """Test add_station creates a new station when it doesn't exist."""
        conn_id = PydanticObjectId("507f1f77bcf86cd799439011")
        now_ts = int(datetime.now().timestamp())
        mock_station_data = MagicMock(spec=DeyeStation)
        mock_station_data.id = 1
        mock_station_data.name = "Test"
        mock_station_data.connection_status = "online"
        mock_station_data.contact_phone = "123"
        mock_station_data.created_date = now_ts
        mock_station_data.grid_interconnection_type = "grid"
        mock_station_data.installed_capacity = 5.0
        mock_station_data.location_address = "addr"
        mock_station_data.location_lat = 0.0
        mock_station_data.location_lng = 0.0
        mock_station_data.owner_name = "owner"
        mock_station_data.region_nation_id = 1
        mock_station_data.region_timezone = "UTC"
        mock_station_data.generation_power = 0
        mock_station_data.last_update_time = now_ts
        mock_station_data.start_operating_time = now_ts

        mock_max_station = MagicMock(spec=Station)
        mock_max_station.order = 5
        mock_new_record = MagicMock()
        mock_new_record.insert = AsyncMock()

        with patch.object(Station, 'find') as mock_find:
            mock_find.return_value.sort.return_value.first_or_none = AsyncMock(return_value=mock_max_station)
            with patch.object(Station, 'find_one', new_callable=AsyncMock) as mock_find_one:
                mock_find_one.return_value = None
                with patch('app.repositories.implementations.stations.Station') as MockStation:
                    MockStation.find.return_value = mock_find.return_value
                    MockStation.find_one = mock_find_one
                    MockStation.return_value = mock_new_record
                    repo = StationsRepository()
                    await repo.add_station(mock_station_data, conn_id)
                    mock_new_record.insert.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_station_existing(self):
        """Test add_station updates an existing station."""
        conn_id = PydanticObjectId("507f1f77bcf86cd799439011")
        now_ts = int(datetime.now().timestamp())
        mock_station_data = MagicMock(spec=DeyeStation)
        mock_station_data.id = 1
        mock_station_data.connection_status = 1
        mock_station_data.grid_interconnection_type = 0
        mock_station_data.last_update_time = now_ts

        mock_max_station = None
        mock_existing = MagicMock(spec=Station)
        mock_existing.save = AsyncMock()

        with patch.object(Station, 'find') as mock_find:
            mock_find.return_value.sort.return_value.first_or_none = AsyncMock(return_value=mock_max_station)
            with patch.object(Station, 'find_one', new_callable=AsyncMock) as mock_find_one:
                mock_find_one.return_value = mock_existing
                repo = StationsRepository()
                await repo.add_station(mock_station_data, conn_id)
                assert mock_existing.connection_status == 1
                mock_existing.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_station_exception(self):
        """Test add_station handles exceptions gracefully."""
        conn_id = PydanticObjectId("507f1f77bcf86cd799439011")
        mock_station_data = MagicMock(spec=DeyeStation)

        with patch.object(Station, 'find', side_effect=Exception("DB error")):
            repo = StationsRepository()
            await repo.add_station(mock_station_data, conn_id)  # Should not raise
