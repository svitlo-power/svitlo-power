"""Tests for app/models/date_value.py."""
from datetime import datetime, time, timezone

import pytest

from app.models.date_value import DateValue


class TestDateValueFromString:
    def test_valid_iso_string(self):
        result = DateValue.from_string("2024-01-01T12:30:00")
        assert result.value == datetime(2024, 1, 1, 12, 30)

    def test_with_z_suffix(self):
        result = DateValue.from_string("2024-01-01T12:30:00Z")
        assert result.value == datetime(2024, 1, 1, 12, 30, tzinfo=timezone.utc)

    def test_invalid_format_raises_value_error(self):
        with pytest.raises(ValueError, match="Invalid datetime format"):
            DateValue.from_string("not-a-date")

    def test_empty_string_raises_value_error(self):
        with pytest.raises(ValueError, match="Invalid datetime format"):
            DateValue.from_string("")


class TestDateValueToMongoQuery:
    def test_to_mongo_query(self):
        dt = datetime(2024, 1, 15, 10, 30, 45, tzinfo=timezone.utc)
        dv = DateValue(value=dt)
        result = dv.to_mongo_query("date_field")
        assert "date_field" in result
        assert result["date_field"]["$gte"] == datetime(2024, 1, 15, 0, 0, tzinfo=timezone.utc)
        assert result["date_field"]["$lte"] == datetime(2024, 1, 15, 23, 59, 59, 999999, tzinfo=timezone.utc)

    def test_to_mongo_query_with_different_field(self):
        dt = datetime(2024, 6, 15, 12, 0, tzinfo=timezone.utc)
        dv = DateValue(value=dt)
        result = dv.to_mongo_query("timestamp")
        assert "timestamp" in result
