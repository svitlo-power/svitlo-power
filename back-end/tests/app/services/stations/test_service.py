"""Tests for app/services/stations/service.py."""
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from beanie import PydanticObjectId

from app.services.stations.service import StationsService
from shared.models.station import Station
from shared.models.station_data import StationData


class TestStationsServiceInit:
    def test_init_stores_dependencies(self):
        mock_events = MagicMock()
        mock_station_connections = MagicMock()
        mock_stations_repo = MagicMock()
        mock_stations_data_repo = MagicMock()

        service = StationsService(mock_events, mock_station_connections, mock_stations_repo, mock_stations_data_repo)
        assert service._station_connections is mock_station_connections
        assert service._stations is mock_stations_repo
        assert service._stations_data is mock_stations_data_repo


class TestStationsServiceGetStations:
    @pytest.mark.asyncio
    async def test_get_stations_delegates_to_repository(self):
        mock_events = MagicMock()
        mock_station_connections = MagicMock()
        mock_stations_repo = MagicMock()
        mock_stations_data_repo = MagicMock()

        stations = [Station(station_id=1, station_name="Station 1"), Station(station_id=2, station_name="Station 2")]
        mock_stations_repo.get_stations = AsyncMock(return_value=stations)

        service = StationsService(mock_events, mock_station_connections, mock_stations_repo, mock_stations_data_repo)
        result = await service.get_stations()
        assert result == stations
        mock_stations_repo.get_stations.assert_called_once_with(all=True)


class TestStationsServiceGetStationData:
    @pytest.mark.asyncio
    async def test_get_station_data_returns_station_and_data(self):
        mock_events = MagicMock()
        mock_station_connections = MagicMock()
        mock_stations_repo = MagicMock()
        mock_stations_data_repo = MagicMock()

        station = Station(station_id=1, station_name="Test Station")
        station_data = [StationData(station_id=station.id, battery_soc=85.0)]
        mock_stations_repo.get_station = AsyncMock(return_value=station)
        mock_stations_data_repo.get_full_station_data = AsyncMock(return_value=station_data)

        service = StationsService(mock_events, mock_station_connections, mock_stations_repo, mock_stations_data_repo)
        result_station, result_data = await service.get_station_data(str(station.id), 3600)
        assert result_station == station
        assert result_data == station_data

    @pytest.mark.asyncio
    async def test_get_station_data_returns_none_when_station_not_found(self):
        mock_events = MagicMock()
        mock_station_connections = MagicMock()
        mock_stations_repo = MagicMock()
        mock_stations_data_repo = MagicMock()

        mock_stations_repo.get_station = AsyncMock(return_value=None)

        service = StationsService(mock_events, mock_station_connections, mock_stations_repo, mock_stations_data_repo)
        result_station, result_data = await service.get_station_data("nonexistent", 3600)
        assert result_station is None
        assert result_data is None


class TestStationsServiceGetStationsData:
    @pytest.mark.asyncio
    async def test_get_stations_data_returns_list_of_tuples(self):
        mock_events = MagicMock()
        mock_station_connections = MagicMock()
        mock_stations_repo = MagicMock()
        mock_stations_data_repo = MagicMock()

        station1 = Station(station_id=1, station_name="Station 1")
        station2 = Station(station_id=2, station_name="Station 2")
        mock_stations_repo.get_stations = AsyncMock(return_value=[station1, station2])
        mock_stations_data_repo.get_full_station_data = AsyncMock(return_value=[])

        service = StationsService(mock_events, mock_station_connections, mock_stations_repo, mock_stations_data_repo)
        result = await service.get_stations_data(3600)
        assert len(result) == 2
        assert result[0][0] == station1
        assert result[1][0] == station2


class TestStationsServiceGetStationsDataRange:
    @pytest.mark.asyncio
    async def test_get_stations_data_range_returns_list_of_tuples(self):
        mock_events = MagicMock()
        mock_station_connections = MagicMock()
        mock_stations_repo = MagicMock()
        mock_stations_data_repo = MagicMock()

        station1 = Station(station_id=1, station_name="Station 1")
        mock_stations_repo.get_stations = AsyncMock(return_value=[station1])
        mock_stations_data_repo.get_full_station_data_range = AsyncMock(return_value=[])

        service = StationsService(mock_events, mock_station_connections, mock_stations_repo, mock_stations_data_repo)
        start = datetime.now(timezone.utc)
        end = datetime.now(timezone.utc)
        result = await service.get_stations_data_range(start, end)
        assert len(result) == 1
        assert result[0][0] == station1


class TestStationsServiceEditStation:
    @pytest.mark.asyncio
    async def test_edit_station_delegates_to_repository(self):
        mock_events = MagicMock()
        mock_station_connections = MagicMock()
        mock_stations_repo = MagicMock()
        mock_stations_data_repo = MagicMock()

        mock_stations_repo.edit_station = AsyncMock()

        service = StationsService(mock_events, mock_station_connections, mock_stations_repo, mock_stations_data_repo)
        await service.edit_station("station-id", True, 1, 10.5, "alias")
        mock_stations_repo.edit_station.assert_called_once_with(
            station_id="station-id",
            enabled=True,
            order=1,
            battery_capacity=10.5,
            station_alias="alias",
        )


class TestStationsServiceSyncStations:
    @pytest.mark.asyncio
    async def test_sync_stations_no_connections(self):
        mock_events = MagicMock()
        mock_station_connections = MagicMock()
        mock_stations_repo = MagicMock()
        mock_stations_data_repo = MagicMock()

        mock_station_connections.get_connections = MagicMock(return_value=[])

        service = StationsService(mock_events, mock_station_connections, mock_stations_repo, mock_stations_data_repo)
        await service.sync_stations(None)
        mock_stations_repo.add_station.assert_not_called()

    @pytest.mark.asyncio
    async def test_sync_stations_with_connection_no_client(self):
        mock_events = MagicMock()
        mock_station_connections = MagicMock()
        mock_stations_repo = MagicMock()
        mock_stations_data_repo = MagicMock()

        conn = MagicMock()
        conn.id = PydanticObjectId()
        conn.sync_stations_on_poll = False
        mock_station_connections.get_connections = MagicMock(return_value=[conn])
        mock_station_connections.get_client = AsyncMock(return_value=None)

        service = StationsService(mock_events, mock_station_connections, mock_stations_repo, mock_stations_data_repo)
        await service.sync_stations(None)
        mock_stations_repo.add_station.assert_not_called()

    @pytest.mark.asyncio
    async def test_sync_stations_with_client_and_stations(self):
        mock_events = MagicMock()
        mock_station_connections = MagicMock()
        mock_stations_repo = MagicMock()
        mock_stations_data_repo = MagicMock()

        conn = MagicMock()
        conn.id = PydanticObjectId()
        conn.sync_stations_on_poll = False
        mock_station_connections.get_connections = MagicMock(return_value=[conn])

        mock_client = MagicMock()
        mock_client.get_station_list = AsyncMock(return_value=None)
        mock_station_connections.get_client = AsyncMock(return_value=mock_client)

        service = StationsService(mock_events, mock_station_connections, mock_stations_repo, mock_stations_data_repo)
        await service.sync_stations(None)
        mock_stations_repo.add_station.assert_not_called()


class TestStationsServiceSyncStationsData:
    @pytest.mark.asyncio
    async def test_sync_stations_data_no_stations(self):
        mock_events = MagicMock()
        mock_events.broadcast_public = AsyncMock()
        mock_station_connections = MagicMock()
        mock_stations_repo = MagicMock()
        mock_stations_data_repo = MagicMock()

        mock_stations_repo.get_stations = AsyncMock(return_value=[])

        service = StationsService(mock_events, mock_station_connections, mock_stations_repo, mock_stations_data_repo)
        await service.sync_stations_data()
        mock_stations_data_repo.add_station_data.assert_not_called()

    @pytest.mark.asyncio
    async def test_sync_stations_data_with_stations_no_client(self):
        mock_events = MagicMock()
        mock_events.broadcast_public = AsyncMock()
        mock_station_connections = MagicMock()
        mock_stations_repo = MagicMock()
        mock_stations_data_repo = MagicMock()

        station = Station(station_id=1, station_name="Test", connection_id=PydanticObjectId())
        mock_stations_repo.get_stations = AsyncMock(return_value=[station])
        mock_station_connections.get_client = AsyncMock(return_value=None)

        service = StationsService(mock_events, mock_station_connections, mock_stations_repo, mock_stations_data_repo)
        await service.sync_stations_data()
        mock_stations_data_repo.add_station_data.assert_not_called()

    @pytest.mark.asyncio
    async def test_sync_stations_with_connection_ids_filter(self):
        """Test sync_stations filters by connection_ids."""
        mock_events = MagicMock()
        mock_station_connections = MagicMock()
        mock_stations_repo = MagicMock()
        mock_stations_data_repo = MagicMock()

        conn1 = MagicMock()
        conn1.id = PydanticObjectId()
        conn1.sync_stations_on_poll = False
        conn2 = MagicMock()
        conn2.id = PydanticObjectId()
        conn2.sync_stations_on_poll = False
        mock_station_connections.get_connections = MagicMock(return_value=[conn1, conn2])

        mock_client = MagicMock()
        mock_client.get_station_list = AsyncMock(return_value=None)
        mock_station_connections.get_client = AsyncMock(return_value=mock_client)

        service = StationsService(mock_events, mock_station_connections, mock_stations_repo, mock_stations_data_repo)
        await service.sync_stations([conn1.id])
        # Only conn1 should be processed
        mock_station_connections.get_client.assert_called_once_with(conn1.id)

    @pytest.mark.asyncio
    async def test_sync_stations_with_client_and_stations(self):
        """Test sync_stations with client and station list."""
        mock_events = MagicMock()
        mock_station_connections = MagicMock()
        mock_stations_repo = MagicMock()
        mock_stations_data_repo = MagicMock()

        conn = MagicMock()
        conn.id = PydanticObjectId()
        conn.sync_stations_on_poll = False
        mock_station_connections.get_connections = MagicMock(return_value=[conn])

        mock_station_list = MagicMock()
        mock_station_list.station_list = [MagicMock(), MagicMock()]
        mock_client = MagicMock()
        mock_client.get_station_list = AsyncMock(return_value=mock_station_list)
        mock_station_connections.get_client = AsyncMock(return_value=mock_client)

        mock_stations_repo.add_station = AsyncMock()

        service = StationsService(mock_events, mock_station_connections, mock_stations_repo, mock_stations_data_repo)
        await service.sync_stations(None)
        assert mock_stations_repo.add_station.call_count == 2

    @pytest.mark.asyncio
    async def test_sync_stations_data_with_client_and_data(self):
        """Test sync_stations_data with client and station data."""
        mock_events = MagicMock()
        mock_events.broadcast_public = AsyncMock()
        mock_station_connections = MagicMock()
        mock_stations_repo = MagicMock()
        mock_stations_data_repo = MagicMock()

        station = Station(station_id=1, station_name="Test", connection_id=PydanticObjectId())
        mock_stations_repo.get_stations = AsyncMock(return_value=[station])

        mock_station_data = MagicMock()
        mock_client = MagicMock()
        mock_client.get_station_data = AsyncMock(return_value=mock_station_data)
        mock_station_connections.get_client = AsyncMock(return_value=mock_client)

        mock_stations_data_repo.add_station_data = AsyncMock()

        service = StationsService(mock_events, mock_station_connections, mock_stations_repo, mock_stations_data_repo)
        await service.sync_stations_data()
        mock_stations_data_repo.add_station_data.assert_called_once_with(station, mock_station_data)
        mock_events.broadcast_public.assert_called_once_with("station_data_updated", None)

    @pytest.mark.asyncio
    async def test_sync_stations_data_with_none_station_data(self):
        """Test sync_stations_data skips when station_data is None."""
        mock_events = MagicMock()
        mock_events.broadcast_public = AsyncMock()
        mock_station_connections = MagicMock()
        mock_stations_repo = MagicMock()
        mock_stations_data_repo = MagicMock()

        station = Station(station_id=1, station_name="Test", connection_id=PydanticObjectId())
        mock_stations_repo.get_stations = AsyncMock(return_value=[station])

        mock_client = MagicMock()
        mock_client.get_station_data = AsyncMock(return_value=None)
        mock_station_connections.get_client = AsyncMock(return_value=mock_client)

        service = StationsService(mock_events, mock_station_connections, mock_stations_repo, mock_stations_data_repo)
        await service.sync_stations_data()
        mock_stations_data_repo.add_station_data.assert_not_called()
