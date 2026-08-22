"""Tests for app/models/date_range_value.py."""
from datetime import datetime, time, timezone

import pytest
from pydantic import ValidationError

from app.models.date_range_value import DateRangeValue


class TestDateRangeValueFromString:
    def test_valid_iso_string(self):
        result = DateRangeValue.from_string("2024-01-01T00:00:00,2024-01-02T00:00:00")
        assert result.start == datetime(2024, 1, 1)
        assert result.end == datetime(2024, 1, 2)

    def test_with_z_suffix(self):
        result = DateRangeValue.from_string("2024-01-01T00:00:00Z,2024-01-02T00:00:00Z")
        assert result.start == datetime(2024, 1, 1, tzinfo=timezone.utc)
        assert result.end == datetime(2024, 1, 2, tzinfo=timezone.utc)

    def test_with_whitespace(self):
        result = DateRangeValue.from_string(" 2024-01-01T00:00:00 , 2024-01-02T00:00:00 ")
        assert result.start == datetime(2024, 1, 1)
        assert result.end == datetime(2024, 1, 2)

    def test_invalid_format_raises_value_error(self):
        with pytest.raises(ValueError, match="Invalid date range format"):
            DateRangeValue.from_string("invalid")

    def test_single_value_raises_value_error(self):
        with pytest.raises(ValueError, match="Invalid date range format"):
            DateRangeValue.from_string("2024-01-01T00:00:00")

    def test_invalid_date_raises_value_error(self):
        with pytest.raises(ValueError, match="Invalid date range format"):
            DateRangeValue.from_string("not-a-date,also-not-a-date")


class TestDateRangeValueToMongoQuery:
    def test_to_mongo_query(self):
        start = datetime(2024, 1, 1, 10, 30, tzinfo=timezone.utc)
        end = datetime(2024, 1, 2, 15, 45, tzinfo=timezone.utc)
        drv = DateRangeValue(start=start, end=end)
        result = drv.to_mongo_query("date_field")
        assert "date_field" in result
        assert result["date_field"]["$gte"] == datetime(2024, 1, 1, tzinfo=timezone.utc)
        assert result["date_field"]["$lte"] == datetime(2024, 1, 2, 23, 59, 59, 999999, tzinfo=timezone.utc)
