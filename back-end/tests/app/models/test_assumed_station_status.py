"""Tests for app/models/assumed_station_status.py."""
from app.models.assumed_station_status import AssumedStationStatus


class TestAssumedStationStatus:
    def test_normal_value(self):
        assert AssumedStationStatus.NORMAL.value == "NORMAL"

    def test_offline_value(self):
        assert AssumedStationStatus.OFFLINE.value == "OFFLINE"

    def test_is_str_enum(self):
        assert isinstance(AssumedStationStatus.NORMAL, str)

    def test_str_representation(self):
        assert str(AssumedStationStatus.NORMAL) == "AssumedStationStatus.NORMAL"

    def test_comparison(self):
        assert AssumedStationStatus.NORMAL == "NORMAL"
        assert AssumedStationStatus.OFFLINE == "OFFLINE"
