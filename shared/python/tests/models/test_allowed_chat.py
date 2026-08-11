"""Tests for shared/models/allowed_chat.py."""
from datetime import datetime, timezone

from shared.models.allowed_chat import AllowedChat


class TestAllowedChatFields:
    def test_has_chat_id_field(self):
        assert "chat_id" in AllowedChat.model_fields

    def test_chat_id_defaults_none(self):
        assert AllowedChat.model_fields["chat_id"].default is None

    def test_has_bot_field(self):
        assert "bot" in AllowedChat.model_fields

    def test_has_approve_date_field(self):
        assert "approve_date" in AllowedChat.model_fields

    def test_settings_name(self):
        assert AllowedChat.Settings.name == "allowed_chats"
