"""Tests for shared/models/message.py."""
from datetime import datetime

from shared.models.message import Message


class TestMessageFields:
    def test_has_channel_id_field(self):
        assert "channel_id" in Message.model_fields

    def test_channel_id_defaults_none(self):
        assert Message.model_fields["channel_id"].default is None

    def test_has_name_field(self):
        assert "name" in Message.model_fields

    def test_has_message_template_field(self):
        assert "message_template" in Message.model_fields

    def test_has_should_send_template_field(self):
        assert "should_send_template" in Message.model_fields

    def test_has_timeout_template_field(self):
        assert "timeout_template" in Message.model_fields

    def test_has_template_macros_field(self):
        assert "template_macros" in Message.model_fields

    def test_has_bot_field(self):
        assert "bot" in Message.model_fields

    def test_has_last_sent_time_field(self):
        assert "last_sent_time" in Message.model_fields

    def test_has_enabled_field(self):
        assert "enabled" in Message.model_fields

    def test_enabled_defaults_true(self):
        assert Message.model_fields["enabled"].default is True

    def test_has_language_field(self):
        assert "language" in Message.model_fields

    def test_has_stations_field(self):
        assert "stations" in Message.model_fields

    def test_stations_defaults_empty_list(self):
        from pydantic.fields import PydanticUndefined
        assert Message.model_fields["stations"].default is PydanticUndefined
        assert Message.model_fields["stations"].default_factory is list

    def test_settings_name(self):
        assert Message.Settings.name == "messages"


class TestMessageStr:
    def test_str_representation(self):
        msg = Message(name="test_message", channel_id="ch1")
        s = str(msg)
        assert "test_message" in s
        assert "ch1" in s
