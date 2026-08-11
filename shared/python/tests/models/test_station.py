"""Tests for shared/models/station.py."""
from datetime import datetime

from shared.models.station import Station


class TestStationFields:
    def test_has_station_id_field(self):
        assert "station_id" in Station.model_fields

    def test_station_id_is_required(self):
        from pydantic.fields import PydanticUndefined
        assert Station.model_fields["station_id"].default is PydanticUndefined

    def test_has_station_name_field(self):
        assert "station_name" in Station.model_fields

    def test_has_station_alias_field(self):
        assert "station_alias" in Station.model_fields

    def test_has_location_lat_field(self):
        assert "location_lat" in Station.model_fields

    def test_has_location_lng_field(self):
        assert "location_lng" in Station.model_fields

    def test_has_location_address_field(self):
        assert "location_address" in Station.model_fields

    def test_has_region_nation_id_field(self):
        assert "region_nation_id" in Station.model_fields

    def test_has_region_timezone_field(self):
        assert "region_timezone" in Station.model_fields

    def test_has_grid_interconnection_type_field(self):
        assert "grid_interconnection_type" in Station.model_fields

    def test_has_installed_capacity_field(self):
        assert "installed_capacity" in Station.model_fields

    def test_has_start_operating_time_field(self):
        assert "start_operating_time" in Station.model_fields

    def test_has_created_date_field(self):
        assert "created_date" in Station.model_fields

    def test_has_last_update_time_field(self):
        assert "last_update_time" in Station.model_fields

    def test_has_connection_status_field(self):
        assert "connection_status" in Station.model_fields

    def test_has_contact_phone_field(self):
        assert "contact_phone" in Station.model_fields

    def test_has_owner_name_field(self):
        assert "owner_name" in Station.model_fields

    def test_has_generation_power_field(self):
        assert "generation_power" in Station.model_fields

    def test_has_battery_capacity_field(self):
        assert "battery_capacity" in Station.model_fields

    def test_has_order_field(self):
        assert "order" in Station.model_fields

    def test_order_defaults_1(self):
        assert Station.model_fields["order"].default == 1

    def test_has_enabled_field(self):
        assert "enabled" in Station.model_fields

    def test_enabled_defaults_true(self):
        assert Station.model_fields["enabled"].default is True

    def test_has_connection_id_field(self):
        assert "connection_id" in Station.model_fields

    def test_settings_name(self):
        assert Station.Settings.name == "stations"


class TestStationStr:
    def test_str_representation(self):
        station = Station(station_id=123, station_name="Test Station")
        s = str(station)
        assert "123" in s
        assert "Test Station" in s


class TestStationToDict:
    def test_to_dict_returns_all_fields(self):
        station = Station(
            station_id=123,
            station_name="Test Station",
            station_alias=None,
            location_lat=50.0,
            location_lng=30.0,
            location_address="Test Address",
            region_nation_id=1,
            region_timezone="UTC",
            grid_interconnection_type="type_a",
            installed_capacity=100.0,
            start_operating_time=None,
            created_date=None,
            last_update_time=None,
            connection_status="online",
            contact_phone="123456789",
            owner_name="Owner",
            generation_power=50.0,
            battery_capacity=200.0,
            order=2,
            enabled=True,
            connection_id=None,
        )
        d = station.to_dict()
        assert d["station_id"] == 123
        assert d["station_name"] == "Test Station"
        assert d["location_lat"] == 50.0
        assert d["location_lng"] == 30.0
        assert d["location_address"] == "Test Address"
        assert d["region_nation_id"] == 1
        assert d["region_timezone"] == "UTC"
        assert d["grid_interconnection_type"] == "type_a"
        assert d["installed_capacity"] == 100.0
        assert d["connection_status"] == "online"
        assert d["contact_phone"] == "123456789"
        assert d["owner_name"] == "Owner"
        assert d["generation_power"] == 50.0
        assert d["battery_capacity"] == 200.0
        assert d["order"] == 2
        assert d["enabled"] is True
        assert d["connection_id"] is None
