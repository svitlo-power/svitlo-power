"""Tests for app/models/station_statistic_data.py."""
from datetime import datetime, timezone

from app.models.station_statistic_data import StationStatisticData


class TestStationStatisticData:
    def test_init_with_both_previous_and_current(self):
        prev = _MockStationData()
        curr = _MockStationData()
        data = StationStatisticData(prev, curr)
        assert data._previous is prev
        assert data._current is curr

    def test_init_with_none_previous(self):
        curr = _MockStationData()
        data = StationStatisticData(None, curr)
        assert data._previous is None
        assert data._current is curr

    def test_init_with_none_current(self):
        prev = _MockStationData()
        data = StationStatisticData(prev, None)
        assert data._previous is prev
        assert data._current is None

    def test_to_dict_with_both(self):
        prev = _MockStationData()
        curr = _MockStationData()
        data = StationStatisticData(prev, curr)
        result = data.to_dict()
        assert "previous" in result
        assert "current" in result
        assert result["previous"] == prev.to_dict(timezone.utc)
        assert result["current"] == curr.to_dict(timezone.utc)

    def test_to_dict_with_none_previous(self):
        curr = _MockStationData()
        data = StationStatisticData(None, curr)
        result = data.to_dict()
        assert result["previous"] is None
        assert result["current"] == curr.to_dict(timezone.utc)

    def test_to_dict_with_none_current(self):
        prev = _MockStationData()
        data = StationStatisticData(prev, None)
        result = data.to_dict()
        assert result["previous"] == prev.to_dict(timezone.utc)
        assert result["current"] is None

    def test_to_dict_with_custom_timezone(self):
        prev = _MockStationData()
        curr = _MockStationData()
        data = StationStatisticData(prev, curr)
        tz = timezone.utc
        result = data.to_dict(tz=tz)
        assert result["previous"] == prev.to_dict(tz)
        assert result["current"] == curr.to_dict(tz)


class _MockStationData:
    def to_dict(self, tz=None):
        return {"mock": "data", "tz": str(tz) if tz else None}
