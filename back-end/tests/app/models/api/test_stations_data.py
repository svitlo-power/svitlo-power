"""Tests for app/models/api/stations_data.py."""
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.models.api import StationsDataRequest


class TestStationsDataRequest:
    def test_valid_with_last_seconds(self):
        req = StationsDataRequest(lastSeconds=3600)
        assert req.last_seconds == 3600
        assert req.start_date is None
        assert req.end_date is None
        assert req.records_count == 250

    def test_valid_with_date_range(self):
        start = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end = datetime(2024, 1, 2, tzinfo=timezone.utc)
        req = StationsDataRequest(startDate=start, endDate=end)
        assert req.start_date == start
        assert req.end_date == end
        assert req.last_seconds is None

    def test_custom_records_count(self):
        req = StationsDataRequest(lastSeconds=3600, recordsCount=100)
        assert req.records_count == 100

    def test_both_last_seconds_and_range_raises_error(self):
        start = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end = datetime(2024, 1, 2, tzinfo=timezone.utc)
        with pytest.raises(ValidationError, match="Provide either lastSeconds OR startDate"):
            StationsDataRequest(lastSeconds=3600, startDate=start, endDate=end)

    def test_only_start_date_raises_error(self):
        start = datetime(2024, 1, 1, tzinfo=timezone.utc)
        with pytest.raises(ValidationError, match="Both startDate and endDate must be provided together"):
            StationsDataRequest(startDate=start)

    def test_only_end_date_raises_error(self):
        end = datetime(2024, 1, 2, tzinfo=timezone.utc)
        with pytest.raises(ValidationError, match="Both startDate and endDate must be provided together"):
            StationsDataRequest(endDate=end)

    def test_start_after_end_raises_error(self):
        start = datetime(2024, 1, 2, tzinfo=timezone.utc)
        end = datetime(2024, 1, 1, tzinfo=timezone.utc)
        with pytest.raises(ValidationError, match="startDate must be earlier than endDate"):
            StationsDataRequest(startDate=start, endDate=end)

    def test_no_params_raises_error(self):
        with pytest.raises(ValidationError, match="You must provide either lastSeconds"):
            StationsDataRequest()
