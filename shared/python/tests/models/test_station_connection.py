"""Tests for shared/models/station_connection.py."""
from shared.models.station_connection import StationConnection


class TestStationConnection:
    def test_has_name_field(self):
        assert "name" in StationConnection.model_fields

    def test_has_base_url_field(self):
        assert "base_url" in StationConnection.model_fields

    def test_has_app_id_field(self):
        assert "app_id" in StationConnection.model_fields

    def test_has_app_secret_field(self):
        assert "app_secret" in StationConnection.model_fields

    def test_has_email_field(self):
        assert "email" in StationConnection.model_fields

    def test_has_password_field(self):
        assert "password" in StationConnection.model_fields

    def test_has_sync_stations_on_poll_field(self):
        assert "sync_stations_on_poll" in StationConnection.model_fields

    def test_sync_stations_on_poll_defaults_false(self):
        assert StationConnection.model_fields["sync_stations_on_poll"].default is False

    def test_settings_name(self):
        assert StationConnection.Settings.name == "station_connections"
