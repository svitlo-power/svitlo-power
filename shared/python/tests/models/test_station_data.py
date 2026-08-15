"""Tests for shared/models/station_data.py."""
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from shared.models.station_data import StationData


class TestStationDataFields:
    def test_has_station_id_field(self):
        assert "station_id" in StationData.model_fields

    def test_station_id_is_required(self):
        from pydantic.fields import PydanticUndefined
        assert StationData.model_fields["station_id"].default is PydanticUndefined

    def test_has_battery_power_field(self):
        assert "battery_power" in StationData.model_fields

    def test_has_battery_soc_field(self):
        assert "battery_soc" in StationData.model_fields

    def test_has_charge_power_field(self):
        assert "charge_power" in StationData.model_fields

    def test_has_code_field(self):
        assert "code" in StationData.model_fields

    def test_has_consumption_power_field(self):
        assert "consumption_power" in StationData.model_fields

    def test_has_discharge_power_field(self):
        assert "discharge_power" in StationData.model_fields

    def test_has_generation_power_field(self):
        assert "generation_power" in StationData.model_fields

    def test_has_grid_power_field(self):
        assert "grid_power" in StationData.model_fields

    def test_has_irradiate_intensity_field(self):
        assert "irradiate_intensity" in StationData.model_fields

    def test_has_last_update_time_field(self):
        assert "last_update_time" in StationData.model_fields

    def test_has_msg_field(self):
        assert "msg" in StationData.model_fields

    def test_has_purchase_power_field(self):
        assert "purchase_power" in StationData.model_fields

    def test_has_request_id_field(self):
        assert "request_id" in StationData.model_fields

    def test_has_wire_power_field(self):
        assert "wire_power" in StationData.model_fields

    def test_settings_name(self):
        assert StationData.Settings.name == "station_data"

    def test_timeseries_config(self):
        assert StationData.Settings.timeseries["time_field"] == "last_update_time"
        assert StationData.Settings.timeseries["meta_field"] == "station_id"
        assert StationData.Settings.timeseries["granularity"] == "minutes"


class TestStationDataToDict:
    def test_to_dict_with_timezone(self):
        from beanie import PydanticObjectId
        sd = StationData(
            station_id=PydanticObjectId(),
            battery_power=100.0,
            battery_soc=50.0,
            last_update_time=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
        )
        d = sd.to_dict()
        assert d["battery_power"] == 100.0
        assert d["battery_soc"] == 50.0
        assert d["last_update_time"] == datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

    def test_to_dict_without_last_update_time(self):
        from beanie import PydanticObjectId
        sd = StationData(station_id=PydanticObjectId())
        d = sd.to_dict()
        assert d["last_update_time"] is None


class TestStationDataStationProperty:
    @pytest.mark.asyncio
    async def test_station_property(self):
        from beanie import PydanticObjectId
        from shared.models.station import Station

        sd = StationData(station_id=PydanticObjectId())
        mock_station = MagicMock()
        with patch.object(Station, "get", new_callable=AsyncMock, return_value=mock_station):
            result = await sd.station
            assert result == mock_station
