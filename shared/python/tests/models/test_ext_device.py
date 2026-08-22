"""Tests for shared/models/ext_device.py."""
from datetime import datetime, timezone

from shared.models.ext_device import ExtDevice


class TestExtDeviceFields:
    def test_has_mac_address_field(self):
        assert "mac_address" in ExtDevice.model_fields

    def test_has_fw_version_field(self):
        assert "fw_version" in ExtDevice.model_fields

    def test_has_fs_version_field(self):
        assert "fs_version" in ExtDevice.model_fields

    def test_has_uptime_field(self):
        assert "uptime" in ExtDevice.model_fields

    def test_has_updated_at_field(self):
        assert "updated_at" in ExtDevice.model_fields

    def test_has_user_field(self):
        assert "user" in ExtDevice.model_fields

    def test_user_defaults_none(self):
        assert ExtDevice.model_fields["user"].default is None

    def test_settings_name(self):
        assert ExtDevice.Settings.name == "ext_device"
