"""Tests for app/models/api/chats.py."""
from datetime import datetime, timezone

import pytest
from beanie import PydanticObjectId
from pydantic import ValidationError

from app.models.api import ChatIdRequest, AllowedChatResponse, ChatRequestResponse


class TestChatIdRequest:
    def test_valid_request(self):
        oid = PydanticObjectId()
        req = ChatIdRequest(id=oid)
        assert req.id == oid

    def test_missing_id_raises_error(self):
        with pytest.raises(ValidationError):
            ChatIdRequest()


class TestAllowedChatResponse:
    def test_valid_response(self):
        chat_id = PydanticObjectId()
        bot_id = PydanticObjectId()
        now = datetime.now(timezone.utc)
        resp = AllowedChatResponse(
            id=chat_id,
            chatId="12345",
            chatName="Test Chat",
            botId=bot_id,
            botName="Test Bot",
            approveDate=now,
        )
        assert resp.id == chat_id
        assert resp.chat_id == "12345"
        assert resp.chat_name == "Test Chat"
        assert resp.bot_id == bot_id
        assert resp.bot_name == "Test Bot"
        assert resp.approve_date == now


class TestChatRequestResponse:
    def test_valid_response(self):
        chat_id = PydanticObjectId()
        bot_id = PydanticObjectId()
        now = datetime.now(timezone.utc)
        resp = ChatRequestResponse(
            id=chat_id,
            chatId="12345",
            chatName="Test Chat",
            botId=bot_id,
            botName="Test Bot",
            requestDate=now,
        )
        assert resp.id == chat_id
        assert resp.chat_id == "12345"
        assert resp.chat_name == "Test Chat"
        assert resp.bot_id == bot_id
        assert resp.bot_name == "Test Bot"
        assert resp.request_date == now
