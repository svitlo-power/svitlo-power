"""Tests for shared/models/ext_data.py."""
from datetime import datetime, timezone

from shared.models.ext_data import ExtData


class TestExtDataFields:
    def test_has_user_id_field(self):
        assert "user_id" in ExtData.model_fields

    def test_has_grid_state_field(self):
        assert "grid_state" in ExtData.model_fields

    def test_grid_state_defaults_false(self):
        assert ExtData.model_fields["grid_state"].default is False

    def test_has_received_at_field(self):
        assert "received_at" in ExtData.model_fields

    def test_settings_name(self):
        assert ExtData.Settings.name == "ext_data"

    def test_timeseries_config(self):
        assert ExtData.Settings.timeseries["time_field"] == "received_at"
        assert ExtData.Settings.timeseries["meta_field"] == "user_id"
        assert ExtData.Settings.timeseries["granularity"] == "minutes"


class TestExtDataStr:
    def test_str_representation(self):
        from beanie import PydanticObjectId
        ext_data = ExtData(user_id=PydanticObjectId(), grid_state=True)
        s = str(ext_data)
        assert "ExtData" in s
        assert "grid_state=True" in s


class TestExtDataToDict:
    def test_to_dict(self):
        from beanie import PydanticObjectId
        ext_data = ExtData(
            user_id=PydanticObjectId(),
            grid_state=True,
            received_at=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
        )
        d = ext_data.to_dict()
        assert d["grid_state"] is True
        assert d["received_at"] == "2024-01-01T12:00:00+00:00"
