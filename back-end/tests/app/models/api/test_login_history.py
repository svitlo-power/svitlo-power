"""Tests for app/models/api/login_history.py."""
from datetime import datetime, timezone

import pytest
from beanie import PydanticObjectId
from pydantic import ValidationError

from app.models.api import LoginHistoryItemResponse


class TestLoginHistoryItemResponse:
    def test_valid_response(self):
        oid = PydanticObjectId()
        now = datetime.now(timezone.utc)
        resp = LoginHistoryItemResponse(
            id=oid,
            loginTime=now,
            ipAddress="192.168.1.1",
        )
        assert resp.id == oid
        assert resp.login_time == now
        assert resp.ip_address == "192.168.1.1"

    def test_response_without_ip(self):
        oid = PydanticObjectId()
        now = datetime.now(timezone.utc)
        resp = LoginHistoryItemResponse(
            id=oid,
            loginTime=now,
        )
        assert resp.ip_address is None

    def test_missing_id_raises_error(self):
        now = datetime.now(timezone.utc)
        with pytest.raises(ValidationError):
            LoginHistoryItemResponse(loginTime=now, ipAddress="192.168.1.1")

    def test_missing_login_time_raises_error(self):
        oid = PydanticObjectId()
        with pytest.raises(ValidationError):
            LoginHistoryItemResponse(id=oid, ipAddress="192.168.1.1")
