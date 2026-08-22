"""Tests for shared/models/login_history.py."""
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from shared.models.login_history import LoginHistory


class TestLoginHistoryFields:
    def test_has_user_id_field(self):
        assert "user_id" in LoginHistory.model_fields

    def test_user_id_is_required(self):
        from pydantic.fields import PydanticUndefined
        assert LoginHistory.model_fields["user_id"].default is PydanticUndefined

    def test_has_login_time_field(self):
        assert "login_time" in LoginHistory.model_fields

    def test_login_time_has_default(self):
        # login_time has a default_factory that returns datetime.now(timezone.utc)
        assert LoginHistory.model_fields["login_time"].default is not None

    def test_has_ip_address_field(self):
        assert "ip_address" in LoginHistory.model_fields

    def test_ip_address_defaults_none(self):
        assert LoginHistory.model_fields["ip_address"].default is None

    def test_settings_name(self):
        assert LoginHistory.Settings.name == "login_history"


class TestLoginHistoryToDict:
    def test_to_dict(self):
        from beanie import PydanticObjectId
        lh = LoginHistory(
            user_id=PydanticObjectId(),
            ip_address="192.168.1.1",
            login_time=datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
        )
        d = lh.to_dict()
        assert d["ip_address"] == "192.168.1.1"
        assert d["login_time"] == "2024-01-01T12:00:00+00:00"

    def test_to_dict_without_ip(self):
        from beanie import PydanticObjectId
        lh = LoginHistory(user_id=PydanticObjectId())
        d = lh.to_dict()
        assert d["ip_address"] is None


class TestLoginHistoryUserProperty:
    @pytest.mark.asyncio
    async def test_user_property(self):
        from beanie import PydanticObjectId
        from shared.models.user import User

        lh = LoginHistory(user_id=PydanticObjectId())
        mock_user = MagicMock()
        with patch.object(User, "get", new_callable=AsyncMock, return_value=mock_user):
            result = await lh.user
            assert result == mock_user
