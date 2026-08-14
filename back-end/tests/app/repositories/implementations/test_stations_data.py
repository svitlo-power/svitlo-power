"""Tests for app/repositories/implementations/stations_data.py."""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch, call
from datetime import datetime, timezone, timedelta
from beanie import PydanticObjectId

from app.repositories.implementations.stations_data import StationsDataRepository
from shared.models.station import Station
from shared.models import StationData
from app.models import AssumedStationStatus
from app.settings import Settings

# Mock Beanie class-level query attributes that are used as query expressions
Station.station_id = MagicMock()
Station.id = MagicMock()

# StationData attributes need to be MagicMock so comparison operators (>=, <) don't crash
# when evaluated BEFORE calling find() in production code
StationData.station_id = MagicMock()
_lut_mock = MagicMock()
_lut_mock.__lt__ = MagicMock(return_value=MagicMock())
_lut_mock.__le__ = MagicMock(return_value=MagicMock())
_lut_mock.__gt__ = MagicMock(return_value=MagicMock())
_lut_mock.__ge__ = MagicMock(return_value=MagicMock())
StationData.last_update_time = _lut_mock




def make_repo():
    settings = MagicMock(spec=Settings)
    settings.DEYE_REPORT_INTERVAL = 300
    settings.DEYE_ASSUMED_OFFLINE_REPORTS = 2
    return StationsDataRepository(settings), settings


def _configure_sd_mock_comparisons(MockSD):
    """Configure MockSD.last_update_time to support comparison operators."""
    lut = MagicMock()
    lut.__lt__ = MagicMock(return_value=MagicMock())
    lut.__le__ = MagicMock(return_value=MagicMock())
    lut.__gt__ = MagicMock(return_value=MagicMock())
    lut.__ge__ = MagicMock(return_value=MagicMock())
    MockSD.last_update_time = lut

class TestStationsDataRepository:
    """Tests for StationsDataRepository."""

    @pytest.mark.asyncio
    async def test_add_station_data_new_record(self):
        """Test add_station_data when no existing record (mock constructor to avoid Pydantic validation)."""
        repo, _ = make_repo()
        station = MagicMock(spec=Station)
        station.id = PydanticObjectId("507f1f77bcf86cd799439011")
        station_data = MagicMock()
        station_data.last_update_time = int(datetime.now().timestamp())
        station_data.battery_power = 100.0
        station_data.battery_soc = 80.0
        station_data.charge_power = 50.0
        station_data.code = "ok"
        station_data.consumption_power = 200.0
        station_data.discharge_power = 0.0
        station_data.generation_power = 150.0
        station_data.grid_power = 0.0
        station_data.irradiate_intensity = 500.0
        station_data.msg = ""
        station_data.purchase_power = 0.0
        station_data.request_id = "req1"
        station_data.wire_power = 0.0

        mock_new_record = MagicMock()
        mock_new_record.insert = AsyncMock()

        with patch.object(StationData, 'find_one', new_callable=AsyncMock) as mock_find_one:
            mock_find_one.return_value = None
            with patch('app.repositories.implementations.stations_data.StationData') as MockStationData:
                MockStationData.return_value = mock_new_record
                MockStationData.find_one = mock_find_one
                await repo.add_station_data(station, station_data)
                mock_new_record.insert.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_station_data_existing_record(self):
        """Test add_station_data when record already exists (skip)."""
        repo, _ = make_repo()
        station = MagicMock(spec=Station)
        station.id = PydanticObjectId("507f1f77bcf86cd799439011")
        station_data = MagicMock()
        station_data.last_update_time = int(datetime.now().timestamp())

        with patch.object(StationData, 'find_one', new_callable=AsyncMock) as mock_find_one:
            mock_find_one.return_value = MagicMock(spec=StationData)
            with patch.object(StationData, 'insert', new_callable=AsyncMock) as mock_insert:
                await repo.add_station_data(station, station_data)
                mock_insert.assert_not_called()

    @pytest.mark.asyncio
    async def test_add_station_data_exception(self):
        """Test add_station_data handles exception gracefully."""
        repo, _ = make_repo()
        station = MagicMock(spec=Station)
        station.id = PydanticObjectId("507f1f77bcf86cd799439011")
        station_data = MagicMock()
        station_data.last_update_time = int(datetime.now().timestamp())

        with patch.object(StationData, 'find_one', side_effect=Exception("DB error")):
            await repo.add_station_data(station, station_data)  # Should not raise

    @pytest.mark.asyncio
    async def test_get_full_station_data(self):
        """Test get_full_station_data (patch StationData class entirely in module)."""
        repo, _ = make_repo()
        station_id = PydanticObjectId("507f1f77bcf86cd799439011")
        mock_list = [MagicMock()]

        with patch('app.repositories.implementations.stations_data.StationData') as MockSD:
            _configure_sd_mock_comparisons(MockSD)
            chain = MockSD.find.return_value.sort.return_value
            chain.to_list = AsyncMock(return_value=mock_list)
            result = await repo.get_full_station_data(station_id, 3600)
            assert result == mock_list

    @pytest.mark.asyncio
    async def test_get_full_station_data_exception(self):
        """Test get_full_station_data exception returns empty list."""
        repo, _ = make_repo()
        station_id = PydanticObjectId("507f1f77bcf86cd799439011")

        with patch('app.repositories.implementations.stations_data.StationData') as MockSD:
            MockSD.find.side_effect = Exception("DB error")
            result = await repo.get_full_station_data(station_id, 3600)
            assert result == []

    @pytest.mark.asyncio
    async def test_get_full_station_data_range_with_tz(self):
        """Test get_full_station_data_range with tz-aware dates."""
        repo, _ = make_repo()
        station_id = "station1"
        start = datetime.now(timezone.utc)
        end = start + timedelta(hours=1)
        mock_list = [MagicMock()]

        with patch('app.repositories.implementations.stations_data.StationData') as MockSD:
            _configure_sd_mock_comparisons(MockSD)
            chain = MockSD.find.return_value.sort.return_value
            chain.to_list = AsyncMock(return_value=mock_list)
            result = await repo.get_full_station_data_range(station_id, start, end)
            assert result == mock_list

    @pytest.mark.asyncio
    async def test_get_full_station_data_range_without_tz(self):
        """Test get_full_station_data_range with tz-naive dates."""
        repo, _ = make_repo()
        station_id = "station1"
        start = datetime.now()  # tz-naive
        end = start + timedelta(hours=1)  # tz-naive
        mock_list = [MagicMock()]

        with patch('app.repositories.implementations.stations_data.StationData') as MockSD:
            _configure_sd_mock_comparisons(MockSD)
            chain = MockSD.find.return_value.sort.return_value
            chain.to_list = AsyncMock(return_value=mock_list)
            result = await repo.get_full_station_data_range(station_id, start, end)
            assert result == mock_list

    @pytest.mark.asyncio
    async def test_get_full_station_data_range_exception(self):
        """Test get_full_station_data_range exception returns empty list."""
        repo, _ = make_repo()
        station_id = "station1"
        start = datetime.now(timezone.utc)
        end = start + timedelta(hours=1)

        with patch('app.repositories.implementations.stations_data.StationData') as MockSD:
            MockSD.find.side_effect = Exception("DB error")
            result = await repo.get_full_station_data_range(station_id, start, end)
            assert result == []

    @pytest.mark.asyncio
    async def test_get_last_station_data(self):
        """Test get_last_station_data."""
        repo, _ = make_repo()
        station_id = PydanticObjectId("507f1f77bcf86cd799439011")
        mock_data = MagicMock(spec=StationData)

        with patch.object(StationData, 'find') as mock_find:
            mock_find.return_value.sort.return_value.first_or_none = AsyncMock(return_value=mock_data)
            result = await repo.get_last_station_data(station_id)
            assert result == mock_data

    @pytest.mark.asyncio
    async def test_get_station_data_average_column_invalid_field(self):
        """Test get_station_data_average_column with invalid field raises ValueError."""
        repo, _ = make_repo()
        with pytest.raises(ValueError):
            await repo.get_station_data_average_column(None, None, 1, "nonexistent_field")

    @pytest.mark.asyncio
    async def test_get_station_data_average_column_non_numeric(self):
        """Test get_station_data_average_column with non-numeric field raises TypeError."""
        repo, _ = make_repo()
        # 'request_id' is a string field in StationData
        with pytest.raises(TypeError):
            await repo.get_station_data_average_column(None, None, 1, "request_id")

    @pytest.mark.asyncio
    async def test_get_station_data_average_column_no_result(self):
        """Test get_station_data_average_column with no result returns 0.0."""
        repo, _ = make_repo()
        with patch('app.repositories.implementations.stations_data.StationData') as MockSD:
            MockSD.model_fields = StationData.model_fields  # Use real fields for validation
            MockSD.aggregate.return_value.to_list = AsyncMock(return_value=[])
            result = await repo.get_station_data_average_column(None, None, 1, "battery_soc")
            assert result == 0.0

    @pytest.mark.asyncio
    async def test_get_station_data_average_column_with_result(self):
        """Test get_station_data_average_column returns the average value."""
        repo, _ = make_repo()
        with patch('app.repositories.implementations.stations_data.StationData') as MockSD:
            MockSD.model_fields = StationData.model_fields
            MockSD.aggregate.return_value.to_list = AsyncMock(return_value=[{"avg_value": 75.5}])
            result = await repo.get_station_data_average_column(None, None, 1, "battery_soc")
            assert result == 75.5

    @pytest.mark.asyncio
    async def test_get_station_data_average_column_with_dates(self):
        """Test get_station_data_average_column with date filters."""
        repo, _ = make_repo()
        start = datetime.now(timezone.utc)
        end = start + timedelta(hours=1)
        with patch('app.repositories.implementations.stations_data.StationData') as MockSD:
            MockSD.model_fields = StationData.model_fields
            MockSD.aggregate.return_value.to_list = AsyncMock(return_value=[{"avg_value": 42.0}])
            result = await repo.get_station_data_average_column(start, end, 1, "battery_soc")
            assert result == 42.0

    @pytest.mark.asyncio
    async def test_get_station_data_tuple_station_not_found(self):
        """Test get_station_data_tuple when station not found."""
        repo, _ = make_repo()
        with patch.object(Station, 'find_one', new_callable=AsyncMock) as mock_find:
            mock_find.return_value = None
            result = await repo.get_station_data_tuple("station1")
            assert result is None

    @pytest.mark.asyncio
    async def test_get_station_data_tuple_no_data(self):
        """Test get_station_data_tuple when no station data."""
        repo, _ = make_repo()
        mock_station = MagicMock(spec=Station)
        mock_station.id = PydanticObjectId("507f1f77bcf86cd799439011")
        with patch.object(Station, 'find_one', new_callable=AsyncMock) as mock_find:
            mock_find.return_value = mock_station
            with patch('app.repositories.implementations.stations_data.StationData') as MockSD:
                MockSD.find.return_value.sort.return_value.limit.return_value.to_list = AsyncMock(return_value=[])
                result = await repo.get_station_data_tuple("station1")
                assert result is None

    @pytest.mark.asyncio
    async def test_get_station_data_tuple_two_records(self):
        """Test get_station_data_tuple with two records."""
        repo, _ = make_repo()
        mock_station = MagicMock(spec=Station)
        mock_station.id = PydanticObjectId("507f1f77bcf86cd799439011")
        d1 = MagicMock()
        d2 = MagicMock()

        with patch.object(Station, 'find_one', new_callable=AsyncMock) as mock_find:
            mock_find.return_value = mock_station
            with patch('app.repositories.implementations.stations_data.StationData') as MockSD:
                MockSD.find.return_value.sort.return_value.limit.return_value.to_list = AsyncMock(return_value=[d1, d2])
                with patch('app.repositories.implementations.stations_data.StationStatisticData') as mock_stat:
                    mock_stat.return_value = MagicMock()
                    result = await repo.get_station_data_tuple("station1")
                    mock_stat.assert_called_once_with(d2, d1)

    @pytest.mark.asyncio
    async def test_get_station_data_tuple_exception(self):
        """Test get_station_data_tuple exception returns None."""
        repo, _ = make_repo()
        with patch.object(Station, 'find_one', side_effect=Exception("DB error")):
            result = await repo.get_station_data_tuple("station1")
            assert result is None

    @pytest.mark.asyncio
    async def test_delete_old_data(self):
        """Test delete_old_data."""
        repo, _ = make_repo()
        with patch('app.repositories.implementations.stations_data.StationData') as MockSD:
            _configure_sd_mock_comparisons(MockSD)
            MockSD.find.return_value.delete = AsyncMock()
            await repo.delete_old_data(5)
            MockSD.find.assert_called_once()
            MockSD.find.return_value.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_assumed_connection_status_no_data(self):
        """Test get_assumed_connection_status with no data returns OFFLINE."""
        repo, _ = make_repo()
        with patch('app.repositories.implementations.stations_data.StationData') as MockSD:
            MockSD.find.return_value.sort.return_value.limit.return_value.to_list = AsyncMock(return_value=[])
            result = await repo.get_assumed_connection_status(1)
            assert result == AssumedStationStatus.OFFLINE

    @pytest.mark.asyncio
    async def test_get_assumed_connection_status_normal(self):
        """Test get_assumed_connection_status with recent data returns NORMAL."""
        repo, _ = make_repo()
        mock_record = MagicMock()
        # Very recent update
        mock_record.last_update_time = datetime.now(timezone.utc).replace(tzinfo=None)

        with patch('app.repositories.implementations.stations_data.StationData') as MockSD:
            MockSD.find.return_value.sort.return_value.limit.return_value.to_list = AsyncMock(return_value=[mock_record])
            result = await repo.get_assumed_connection_status(1)
            assert result == AssumedStationStatus.NORMAL

    @pytest.mark.asyncio
    async def test_get_assumed_connection_status_offline(self):
        """Test get_assumed_connection_status with old data returns OFFLINE."""
        repo, _ = make_repo()
        mock_record = MagicMock()
        # Very old update (more than 300*2=600 seconds ago)
        old_time = datetime.now(timezone.utc) - timedelta(seconds=700)
        mock_record.last_update_time = old_time.replace(tzinfo=None)

        with patch('app.repositories.implementations.stations_data.StationData') as MockSD:
            MockSD.find.return_value.sort.return_value.limit.return_value.to_list = AsyncMock(return_value=[mock_record])
            result = await repo.get_assumed_connection_status(1)
            assert result == AssumedStationStatus.OFFLINE
