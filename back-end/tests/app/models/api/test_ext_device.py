"""Tests for app/models/api/ext_device.py."""
from datetime import datetime, timezone

import pytest
from beanie import PydanticObjectId
from pydantic import ValidationError

from app.models.api import DevicePingRequest, ExtDeviceResponse


class TestDevicePingRequest:
    def test_valid_request(self):
        req = DevicePingRequest(
            macAddress="00:11:22:33:44:55",
            fwVersion="1.0.0",
            fsVersion="2.0.0",
            uptime=3600,
        )
        assert req.mac_address == "00:11:22:33:44:55"
        assert req.fw_version == "1.0.0"
        assert req.fs_version == "2.0.0"
        assert req.uptime == 3600

    def test_missing_mac_address_raises_error(self):
        with pytest.raises(ValidationError):
            DevicePingRequest(fwVersion="1.0.0", fsVersion="2.0.0", uptime=3600)

    def test_missing_fw_version_raises_error(self):
        with pytest.raises(ValidationError):
            DevicePingRequest(macAddress="00:11:22:33:44:55", fsVersion="2.0.0", uptime=3600)

    def test_missing_fs_version_raises_error(self):
        with pytest.raises(ValidationError):
            DevicePingRequest(macAddress="00:11:22:33:44:55", fwVersion="1.0.0", uptime=3600)

    def test_missing_uptime_raises_error(self):
        with pytest.raises(ValidationError):
            DevicePingRequest(macAddress="00:11:22:33:44:55", fwVersion="1.0.0", fsVersion="2.0.0")


class TestExtDeviceResponse:
    def test_valid_response(self):
        oid = PydanticObjectId()
        now = datetime.now(timezone.utc)
        resp = ExtDeviceResponse(
            macAddress="00:11:22:33:44:55",
            fwVersion="1.0.0",
            fsVersion="2.0.0",
            uptime=3600,
            updatedAt=now,
            userId=oid,
            gridState=True,
        )
        assert resp.mac_address == "00:11:22:33:44:55"
        assert resp.fw_version == "1.0.0"
        assert resp.fs_version == "2.0.0"
        assert resp.uptime == 3600
        assert resp.updated_at == now
        assert resp.user_id == oid
        assert resp.grid_state is True

    def test_response_without_user(self):
        now = datetime.now(timezone.utc)
        resp = ExtDeviceResponse(
            macAddress="00:11:22:33:44:55",
            fwVersion="1.0.0",
            fsVersion="2.0.0",
            uptime=3600,
            updatedAt=now,
        )
        assert resp.user_id is None
        assert resp.grid_state is None
