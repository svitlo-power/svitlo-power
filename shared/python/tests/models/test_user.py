"""Tests for shared/models/user.py."""
import pytest
from datetime import datetime

from shared.models.user import User, ReportMode


class TestReportMode:
    def test_report_mode_ping(self):
        assert ReportMode.PING.value == "ping"

    def test_report_mode_event(self):
        assert ReportMode.EVENT.value == "event"

    def test_report_mode_is_str_enum(self):
        assert isinstance(ReportMode.PING, str)


class TestUserFields:
    def test_has_name_field(self):
        assert "name" in User.model_fields

    def test_has_password_field(self):
        assert "password" in User.model_fields

    def test_password_is_required(self):
        from pydantic.fields import PydanticUndefined
        assert User.model_fields["password"].default is PydanticUndefined

    def test_has_is_active_field(self):
        assert "is_active" in User.model_fields

    def test_is_active_defaults_true(self):
        assert User.model_fields["is_active"].default is True

    def test_has_is_reporter_field(self):
        assert "is_reporter" in User.model_fields

    def test_is_reporter_defaults_false(self):
        assert User.model_fields["is_reporter"].default is False

    def test_has_api_key_field(self):
        assert "api_key" in User.model_fields

    def test_api_key_defaults_none(self):
        assert User.model_fields["api_key"].default is None

    def test_has_password_reset_token_field(self):
        assert "password_reset_token" in User.model_fields

    def test_has_reset_token_expiration_field(self):
        assert "reset_token_expiration" in User.model_fields

    def test_has_report_mode_field(self):
        assert "report_mode" in User.model_fields

    def test_report_mode_defaults_none(self):
        assert User.model_fields["report_mode"].default is None

    def test_settings_name(self):
        assert User.Settings.name == "users"


class TestUserValidation:
    def test_reporter_without_report_mode_raises_error(self):
        with pytest.raises(ValueError, match="report_mode must be set"):
            User(name="test", password="secret", is_reporter=True)

    def test_reporter_with_report_mode_ping(self):
        user = User(name="test", password="secret", is_reporter=True, report_mode=ReportMode.PING)
        assert user.report_mode == ReportMode.PING

    def test_reporter_with_report_mode_event(self):
        user = User(name="test", password="secret", is_reporter=True, report_mode=ReportMode.EVENT)
        assert user.report_mode == ReportMode.EVENT

    def test_non_reporter_report_mode_set_to_none(self):
        user = User(name="test", password="secret", is_reporter=False, report_mode=ReportMode.PING)
        assert user.report_mode is None

    def test_non_reporter_without_report_mode(self):
        user = User(name="test", password="secret", is_reporter=False)
        assert user.report_mode is None


class TestUserStr:
    def test_str_representation(self):
        user = User(name="testuser", password="secret", is_reporter=True, report_mode=ReportMode.PING)
        s = str(user)
        assert "testuser" in s
        assert "is_reporter=True" in s
        assert "report_mode=ReportMode.PING" in s
