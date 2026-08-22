"""Tests for shared/models/chat_request.py."""
from datetime import datetime, timezone

from shared.models.chat_request import ChatRequest


class TestChatRequestFields:
    def test_has_chat_id_field(self):
        assert "chat_id" in ChatRequest.model_fields

    def test_chat_id_defaults_none(self):
        assert ChatRequest.model_fields["chat_id"].default is None

    def test_has_bot_field(self):
        assert "bot" in ChatRequest.model_fields

    def test_has_request_date_field(self):
        assert "request_date" in ChatRequest.model_fields

    def test_settings_name(self):
        assert ChatRequest.Settings.name == "chat_requests"
