"""Tests for app/models/api/messages.py."""
from datetime import datetime, timezone

import pytest
from beanie import PydanticObjectId
from pydantic import ValidationError

from app.models.api import (
    MessageListResponseModel,
    MessageEditResponseModel,
    MessageCreateRequest,
    MessageUpdateRequest,
    MessagePreviewRequest,
    MessagePreviewResponse,
    SaveMessageStateRequest,
)


class TestMessageListResponseModel:
    def test_valid_response(self):
        oid = PydanticObjectId()
        now = datetime.now(timezone.utc)
        resp = MessageListResponseModel(
            id=oid,
            name="Test Message",
            channelName="Test Channel",
            stations=[oid],
            botName="Test Bot",
            lastSentTime=now,
            enabled=True,
        )
        assert resp.id == oid
        assert resp.name == "Test Message"
        assert resp.channel_name == "Test Channel"
        assert resp.stations == [oid]
        assert resp.bot_name == "Test Bot"
        assert resp.last_sent_time == now
        assert resp.enabled is True

    def test_without_last_sent_time(self):
        oid = PydanticObjectId()
        resp = MessageListResponseModel(
            id=oid,
            name="Test",
            channelName="Channel",
            stations=[],
            botName="Bot",
            enabled=True,
        )
        assert resp.last_sent_time is None


class TestMessageEditResponseModel:
    def test_valid_response(self):
        oid = PydanticObjectId()
        now = datetime.now(timezone.utc)
        resp = MessageEditResponseModel(
            id=oid,
            name="Test Message",
            channelId="channel123",
            channelName="Test Channel",
            stations=[oid],
            botId=oid,
            botName="Test Bot",
            lastSentTime=now,
            templateMacros=None,
            messageTemplate="Hello {{ name }}",
            shouldSendTemplate="True",
            timeoutTemplate="300",
            enabled=True,
            language="en",
        )
        assert resp.id == oid
        assert resp.name == "Test Message"
        assert resp.channel_id == "channel123"
        assert resp.message_template == "Hello {{ name }}"
        assert resp.should_send_template == "True"
        assert resp.timeout_template == "300"
        assert resp.language == "en"


class TestMessageCreateRequest:
    def test_valid_request(self):
        oid = PydanticObjectId()
        req = MessageCreateRequest(
            name="Test Message",
            channelId="channel123",
            stations=[oid],
            botId=oid,
            templateMacros=None,
            messageTemplate="Hello",
            shouldSendTemplate="True",
            timeoutTemplate="300",
            enabled=True,
            language="en",
        )
        assert req.name == "Test Message"
        assert req.channel_id == "channel123"
        assert req.message_template == "Hello"
        assert req.enabled is True
        assert req.language == "en"


class TestMessageUpdateRequest:
    def test_inherits_from_create(self):
        oid = PydanticObjectId()
        req = MessageUpdateRequest(
            name="Updated",
            channelId="channel123",
            stations=[oid],
            botId=oid,
            messageTemplate="Updated template",
            shouldSendTemplate="True",
            timeoutTemplate="300",
            enabled=True,
            language="en",
        )
        assert req.name == "Updated"
        assert req.message_template == "Updated template"


class TestMessagePreviewRequest:
    def test_valid_request(self):
        oid = PydanticObjectId()
        req = MessagePreviewRequest(
            name="Test",
            messageTemplate="Hello",
            timeoutTemplate="300",
            shouldSendTemplate="True",
            templateMacros=None,
            stations=[oid],
            language="en",
        )
        assert req.name == "Test"
        assert req.message_template == "Hello"
        assert req.timeout_template == "300"
        assert req.should_send_template == "True"
        assert req.stations == [oid]
        assert req.language == "en"

    def test_with_id(self):
        oid = PydanticObjectId()
        req = MessagePreviewRequest(
            id=oid,
            name="Test",
            messageTemplate="Hello",
            timeoutTemplate="300",
            stations=[],
            language="en",
        )
        assert req.id == oid


class TestMessagePreviewResponse:
    def test_valid_response(self):
        now = datetime.now(timezone.utc)
        resp = MessagePreviewResponse(
            success=True,
            message="Hello World",
            shouldSend=True,
            timeout=300,
            nextSendTime=now,
            data={"key": "value"},
        )
        assert resp.success is True
        assert resp.message == "Hello World"
        assert resp.should_send is True
        assert resp.timeout == 300
        assert resp.next_send_time == now
        assert resp.data == {"key": "value"}


class TestSaveMessageStateRequest:
    def test_default_enabled_false(self):
        req = SaveMessageStateRequest()
        assert req.enabled is False

    def test_enabled_true(self):
        req = SaveMessageStateRequest(enabled=True)
        assert req.enabled is True
