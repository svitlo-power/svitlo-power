"""Tests for shared/models/station_connection.py."""
from shared.models.station_connection import StationConnection


class TestStationConnectionStr:
    def test_str_representation(self):
        sc = StationConnection(
            name="Test Connection",
            base_url="http://test.com",
            app_id="app1",
            app_secret="secret",
            email="test@test.com",
            password="pass",
        )
        s = str(sc)
        assert "Test Connection" in s
        assert "http://test.com" in s
        assert "app1" in s
        assert "test@test.com" in s
        assert "***" in s  # app_secret and password should be masked
        assert "sync_stations_on_poll=False" in s


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
