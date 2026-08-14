"""Tests for app/services/messages/service.py."""
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from beanie import PydanticObjectId

from app.services.messages.service import MessagesService
from app.services.telegram.service import TelegramService
from app.services.interfaces import IMessageGeneratorService, MessageItem
from app.models.api import (
    MessageListResponseModel,
    MessageEditResponseModel,
    MessageCreateRequest,
    MessageUpdateRequest,
    MessagePreviewRequest,
    MessagePreviewResponse,
)
from shared.models.message import Message
from shared.models.bot import Bot
from shared.models.station import Station


class TestMessagesServiceInit:
    def test_init_stores_dependencies(self):
        mock_events = MagicMock()
        mock_messages_repo = MagicMock()
        mock_stations_repo = MagicMock()
        mock_message_generator = MagicMock(spec=IMessageGeneratorService)
        mock_telegram = MagicMock(spec=TelegramService)

        service = MessagesService(mock_events, mock_messages_repo, mock_stations_repo, mock_message_generator, mock_telegram)
        assert service._messages is mock_messages_repo
        assert service._stations is mock_stations_repo
        assert service._message_generator is mock_message_generator
        assert service._telegram is mock_telegram


class TestMessagesServiceGetMessages:
    @pytest.mark.asyncio
    async def test_get_messages_returns_list(self):
        mock_events = MagicMock()
        mock_messages_repo = MagicMock()
        mock_stations_repo = MagicMock()
        mock_message_generator = MagicMock(spec=IMessageGeneratorService)
        mock_telegram = MagicMock(spec=TelegramService)

        bot = Bot(token="token", enabled=True, hook_enabled=True)
        message = Message(name="Test", channel_id="channel", bot=bot, enabled=True, language="en")
        mock_messages_repo.get_messages = AsyncMock(return_value=[message])
        mock_telegram.get_bot_info = AsyncMock(return_value=MagicMock(username="test_bot"))
        mock_telegram.get_chat_info = AsyncMock(return_value=MagicMock(title="Test Channel"))

        service = MessagesService(mock_events, mock_messages_repo, mock_stations_repo, mock_message_generator, mock_telegram)
        result = await service.get_messages(all=True)
        assert len(result) == 1
        assert isinstance(result[0], MessageListResponseModel)
        assert result[0].name == "Test"

    @pytest.mark.asyncio
    async def test_get_messages_empty_list(self):
        mock_events = MagicMock()
        mock_messages_repo = MagicMock()
        mock_stations_repo = MagicMock()
        mock_message_generator = MagicMock(spec=IMessageGeneratorService)
        mock_telegram = MagicMock(spec=TelegramService)

        mock_messages_repo.get_messages = AsyncMock(return_value=[])

        service = MessagesService(mock_events, mock_messages_repo, mock_stations_repo, mock_message_generator, mock_telegram)
        result = await service.get_messages(all=True)
        assert result == []


class TestMessagesServiceGetMessage:
    @pytest.mark.asyncio
    async def test_get_message_returns_edit_response(self):
        mock_events = MagicMock()
        mock_messages_repo = MagicMock()
        mock_stations_repo = MagicMock()
        mock_message_generator = MagicMock(spec=IMessageGeneratorService)
        mock_telegram = MagicMock(spec=TelegramService)

        bot = Bot(token="token", enabled=True, hook_enabled=True)
        message = Message(
            name="Test",
            channel_id="channel",
            bot=bot,
            enabled=True,
            language="en",
            message_template="Hello",
            should_send_template="True",
            timeout_template="300",
        )
        mock_messages_repo.get_message = AsyncMock(return_value=message)
        mock_telegram.get_bot_info = AsyncMock(return_value=MagicMock(username="test_bot"))
        mock_telegram.get_chat_info = AsyncMock(return_value=MagicMock(title="Test Channel"))

        service = MessagesService(mock_events, mock_messages_repo, mock_stations_repo, mock_message_generator, mock_telegram)
        result = await service.get_message(PydanticObjectId())
        assert isinstance(result, MessageEditResponseModel)
        assert result.name == "Test"


class TestMessagesServiceCreateMessage:
    @pytest.mark.asyncio
    async def test_create_message_delegates_to_repository(self):
        mock_events = MagicMock()
        mock_events.broadcast_private = AsyncMock()
        mock_messages_repo = MagicMock()
        mock_stations_repo = MagicMock()
        mock_message_generator = MagicMock(spec=IMessageGeneratorService)
        mock_telegram = MagicMock(spec=TelegramService)

        mock_messages_repo.create = AsyncMock(return_value=MagicMock(id=PydanticObjectId()))

        service = MessagesService(mock_events, mock_messages_repo, mock_stations_repo, mock_message_generator, mock_telegram)
        dto = MessageCreateRequest(
            name="Test",
            channelId="channel",
            stations=[],
            botId=PydanticObjectId(),
            messageTemplate="Hello",
            shouldSendTemplate="True",
            timeoutTemplate="300",
            enabled=True,
            language="en",
        )
        result = await service.create_message(dto)
        assert result is not None
        mock_messages_repo.create.assert_called_once()
        mock_events.broadcast_private.assert_called_once_with("messages_updated", None)


class TestMessagesServiceUpdateMessage:
    @pytest.mark.asyncio
    async def test_update_message_delegates_to_repository(self):
        mock_events = MagicMock()
        mock_events.broadcast_private = AsyncMock()
        mock_messages_repo = MagicMock()
        mock_stations_repo = MagicMock()
        mock_message_generator = MagicMock(spec=IMessageGeneratorService)
        mock_telegram = MagicMock(spec=TelegramService)

        mock_messages_repo.update = AsyncMock(return_value=MagicMock(id=PydanticObjectId()))

        service = MessagesService(mock_events, mock_messages_repo, mock_stations_repo, mock_message_generator, mock_telegram)
        dto = MessageUpdateRequest(
            name="Updated",
            channelId="channel",
            stations=[],
            botId=PydanticObjectId(),
            messageTemplate="Updated",
            shouldSendTemplate="True",
            timeoutTemplate="300",
            enabled=True,
            language="en",
        )
        result = await service.update_message(PydanticObjectId(), dto)
        assert result is not None
        mock_messages_repo.update.assert_called_once()
        mock_events.broadcast_private.assert_called_once_with("messages_updated", None)


class TestMessagesServiceSaveState:
    @pytest.mark.asyncio
    async def test_save_state_delegates_to_repository(self):
        mock_events = MagicMock()
        mock_events.broadcast_private = AsyncMock()
        mock_messages_repo = MagicMock()
        mock_stations_repo = MagicMock()
        mock_message_generator = MagicMock(spec=IMessageGeneratorService)
        mock_telegram = MagicMock(spec=TelegramService)

        mock_messages_repo.save_state = AsyncMock()

        service = MessagesService(mock_events, mock_messages_repo, mock_stations_repo, mock_message_generator, mock_telegram)
        await service.save_state(PydanticObjectId(), True)
        mock_messages_repo.save_state.assert_called_once()
        mock_events.broadcast_private.assert_called_once_with("messages_updated", None)


class TestMessagesServiceGetMessagePreview:
    @pytest.mark.asyncio
    async def test_get_message_preview_success(self):
        mock_events = MagicMock()
        mock_messages_repo = MagicMock()
        mock_stations_repo = MagicMock()
        mock_message_generator = MagicMock(spec=IMessageGeneratorService)
        mock_telegram = MagicMock(spec=TelegramService)

        mock_stations_repo.get_stations = AsyncMock(return_value=[])
        mock_messages_repo.get_message = AsyncMock(return_value=None)

        message_item = MessageItem(
            message="Hello World",
            timeout=300,
            should_send=True,
            next_send_time=datetime.now(timezone.utc),
            data=None,
        )
        mock_message_generator.generate_message = AsyncMock(return_value=message_item)

        service = MessagesService(mock_events, mock_messages_repo, mock_stations_repo, mock_message_generator, mock_telegram)
        dto = MessagePreviewRequest(
            name="Test",
            messageTemplate="Hello",
            timeoutTemplate="300",
            shouldSendTemplate="True",
            stations=[],
            language="en",
        )
        result = await service.get_message_preview(dto)
        assert isinstance(result, MessagePreviewResponse)
        assert result.success is True
        assert result.message == "Hello World"

    @pytest.mark.asyncio
    async def test_get_message_preview_no_message_raises(self):
        mock_events = MagicMock()
        mock_messages_repo = MagicMock()
        mock_stations_repo = MagicMock()
        mock_message_generator = MagicMock(spec=IMessageGeneratorService)
        mock_telegram = MagicMock(spec=TelegramService)

        mock_stations_repo.get_stations = AsyncMock(return_value=[])
        mock_messages_repo.get_message = AsyncMock(return_value=None)
        mock_message_generator.generate_message = AsyncMock(return_value=None)

        service = MessagesService(mock_events, mock_messages_repo, mock_stations_repo, mock_message_generator, mock_telegram)
        dto = MessagePreviewRequest(
            name="Test",
            messageTemplate="Hello",
            timeoutTemplate="300",
            stations=[],
            language="en",
        )
        with pytest.raises(Exception):
            await service.get_message_preview(dto)


class TestMessagesServiceGetBotName:
    @pytest.mark.asyncio
    async def test_get_bot_name_returns_username(self):
        mock_events = MagicMock()
        mock_messages_repo = MagicMock()
        mock_stations_repo = MagicMock()
        mock_message_generator = MagicMock(spec=IMessageGeneratorService)
        mock_telegram = MagicMock(spec=TelegramService)

        mock_telegram.get_bot_info = AsyncMock(return_value=MagicMock(username="test_bot"))

        service = MessagesService(mock_events, mock_messages_repo, mock_stations_repo, mock_message_generator, mock_telegram)
        result = await service._get_bot_name("bot_id_123")
        assert result == "test_bot"

    @pytest.mark.asyncio
    async def test_get_bot_name_returns_invalid_on_error(self):
        mock_events = MagicMock()
        mock_messages_repo = MagicMock()
        mock_stations_repo = MagicMock()
        mock_message_generator = MagicMock(spec=IMessageGeneratorService)
        mock_telegram = MagicMock(spec=TelegramService)

        mock_telegram.get_bot_info = AsyncMock(side_effect=Exception("API error"))

        service = MessagesService(mock_events, mock_messages_repo, mock_stations_repo, mock_message_generator, mock_telegram)
        result = await service._get_bot_name("bot_id_123")
        assert result == "Invalid bot identifier"


class TestMessagesServiceGetChannelName:
    @pytest.mark.asyncio
    async def test_get_channel_name_returns_title(self):
        mock_events = MagicMock()
        mock_messages_repo = MagicMock()
        mock_stations_repo = MagicMock()
        mock_message_generator = MagicMock(spec=IMessageGeneratorService)
        mock_telegram = MagicMock(spec=TelegramService)

        mock_telegram.get_chat_info = AsyncMock(return_value=MagicMock(title="Test Channel"))

        service = MessagesService(mock_events, mock_messages_repo, mock_stations_repo, mock_message_generator, mock_telegram)
        result = await service._get_channel_name("channel_id_123", "bot_id_456")
        assert result == "Test Channel"

    @pytest.mark.asyncio
    async def test_get_channel_name_returns_invalid_on_error(self):
        mock_events = MagicMock()
        mock_messages_repo = MagicMock()
        mock_stations_repo = MagicMock()
        mock_message_generator = MagicMock(spec=IMessageGeneratorService)
        mock_telegram = MagicMock(spec=TelegramService)

        mock_telegram.get_chat_info = AsyncMock(side_effect=Exception("API error"))

        service = MessagesService(mock_events, mock_messages_repo, mock_stations_repo, mock_message_generator, mock_telegram)
        result = await service._get_channel_name("channel_id_123", "bot_id_456")
        assert result == "Invalid channel identifier"


class TestMessagesServiceGetMessagePreviewWithExistingMessage:
    @pytest.mark.asyncio
    async def test_get_message_preview_with_existing_message(self):
        mock_events = MagicMock()
        mock_messages_repo = MagicMock()
        mock_stations_repo = MagicMock()
        mock_message_generator = MagicMock(spec=IMessageGeneratorService)
        mock_telegram = MagicMock(spec=TelegramService)

        bot = Bot(token="token", enabled=True, hook_enabled=True)
        existing_message = Message(
            name="Test",
            channel_id="channel",
            bot=bot,
            enabled=True,
            language="en",
            message_template="Hello",
            should_send_template="True",
            timeout_template="300",
            last_sent_time=datetime.now(timezone.utc),
        )
        mock_stations_repo.get_stations = AsyncMock(return_value=[])
        mock_messages_repo.get_message = AsyncMock(return_value=existing_message)
        mock_message_generator.generate_message = AsyncMock(return_value=MessageItem(
            message="Hello World",
            timeout=300,
            should_send=True,
            next_send_time=datetime.now(timezone.utc),
            data=None,
        ))

        service = MessagesService(mock_events, mock_messages_repo, mock_stations_repo, mock_message_generator, mock_telegram)
        dto = MessagePreviewRequest(
            name="Test",
            messageTemplate="Hello",
            timeoutTemplate="300",
            shouldSendTemplate="True",
            stations=[],
            language="en",
            id=PydanticObjectId(),
        )
        result = await service.get_message_preview(dto)
        assert isinstance(result, MessagePreviewResponse)
        assert result.success is True
