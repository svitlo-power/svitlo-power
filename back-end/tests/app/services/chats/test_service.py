"""Tests for app/services/chats/service.py."""
from unittest.mock import AsyncMock, MagicMock

import pytest
from beanie import PydanticObjectId

from app.services.chats.service import ChatsService
from app.services.telegram.service import TelegramService
from app.models.api import ChatIdRequest, AllowedChatResponse, ChatRequestResponse
from shared.models.allowed_chat import AllowedChat
from shared.models.chat_request import ChatRequest
from shared.models.bot import Bot


class TestChatsServiceInit:
    def test_init_stores_dependencies(self):
        mock_chats_repo = MagicMock()
        mock_telegram = MagicMock(spec=TelegramService)
        mock_events = MagicMock()

        service = ChatsService(mock_chats_repo, mock_telegram, mock_events)
        assert service._chats is mock_chats_repo
        assert service._telegram is mock_telegram


class TestChatsServiceGetChats:
    @pytest.mark.asyncio
    async def test_get_chats_returns_response_list(self):
        mock_chats_repo = MagicMock()
        mock_telegram = MagicMock(spec=TelegramService)
        mock_events = MagicMock()

        bot = Bot(token="token", enabled=True, hook_enabled=True)
        chat = AllowedChat(chat_id="123", bot=bot)
        mock_chats_repo.get_allowed_chats = AsyncMock(return_value=[chat])

        mock_telegram.get_chat_info = AsyncMock(return_value=MagicMock(username="test_chat", title="Test Chat"))
        mock_telegram.get_bot_info = AsyncMock(return_value=MagicMock(username="test_bot"))

        service = ChatsService(mock_chats_repo, mock_telegram, mock_events)
        result = await service.get_chats()
        assert len(result) == 1
        assert isinstance(result[0], AllowedChatResponse)
        assert result[0].chat_name == "test_chat"
        assert result[0].bot_name == "test_bot"

    @pytest.mark.asyncio
    async def test_get_chats_empty_list(self):
        mock_chats_repo = MagicMock()
        mock_telegram = MagicMock(spec=TelegramService)
        mock_events = MagicMock()

        mock_chats_repo.get_allowed_chats = AsyncMock(return_value=[])

        service = ChatsService(mock_chats_repo, mock_telegram, mock_events)
        result = await service.get_chats()
        assert result == []


class TestChatsServiceGetChatRequests:
    @pytest.mark.asyncio
    async def test_get_chat_requests_returns_response_list(self):
        mock_chats_repo = MagicMock()
        mock_telegram = MagicMock(spec=TelegramService)
        mock_events = MagicMock()

        bot = Bot(token="token", enabled=True, hook_enabled=True)
        chat_request = ChatRequest(chat_id="123", bot=bot)
        mock_chats_repo.get_chat_requests = AsyncMock(return_value=[chat_request])

        mock_telegram.get_chat_info = AsyncMock(return_value=MagicMock(username="test_chat", title="Test Chat"))
        mock_telegram.get_bot_info = AsyncMock(return_value=MagicMock(username="test_bot"))

        service = ChatsService(mock_chats_repo, mock_telegram, mock_events)
        result = await service.get_chat_requests()
        assert len(result) == 1
        assert isinstance(result[0], ChatRequestResponse)
        assert result[0].chat_name == "test_chat"


class TestChatsServiceApproveChatRequest:
    @pytest.mark.asyncio
    async def test_approve_chat_request_delegates_to_repository(self):
        mock_chats_repo = MagicMock()
        mock_telegram = MagicMock(spec=TelegramService)
        mock_events = MagicMock()
        mock_events.broadcast_private = AsyncMock()

        mock_chats_repo.approve_chat_request = AsyncMock()

        service = ChatsService(mock_chats_repo, mock_telegram, mock_events)
        request = ChatIdRequest(id=PydanticObjectId())
        await service.approve_chat_request(request)
        mock_chats_repo.approve_chat_request.assert_called_once_with(request.id)
        mock_events.broadcast_private.assert_called_once_with("chats_updated", None)


class TestChatsServiceRejectChatRequest:
    @pytest.mark.asyncio
    async def test_reject_chat_request_delegates_to_repository(self):
        mock_chats_repo = MagicMock()
        mock_telegram = MagicMock(spec=TelegramService)
        mock_events = MagicMock()
        mock_events.broadcast_private = AsyncMock()

        mock_chats_repo.reject_chat_request = AsyncMock()

        service = ChatsService(mock_chats_repo, mock_telegram, mock_events)
        request = ChatIdRequest(id=PydanticObjectId())
        await service.reject_chat_request(request)
        mock_chats_repo.reject_chat_request.assert_called_once_with(request.id)
        mock_events.broadcast_private.assert_called_once_with("chats_updated", None)


class TestChatsServiceDisallowChat:
    @pytest.mark.asyncio
    async def test_disallow_chat_delegates_to_repository(self):
        mock_chats_repo = MagicMock()
        mock_telegram = MagicMock(spec=TelegramService)
        mock_events = MagicMock()
        mock_events.broadcast_private = AsyncMock()

        mock_chats_repo.disallow_chat = AsyncMock()

        service = ChatsService(mock_chats_repo, mock_telegram, mock_events)
        request = ChatIdRequest(id=PydanticObjectId())
        await service.disallow_chat(request)
        mock_chats_repo.disallow_chat.assert_called_once_with(request.id)
        mock_events.broadcast_private.assert_called_once_with("chats_updated", None)


class TestChatsServiceGetBotName:
    @pytest.mark.asyncio
    async def test_get_bot_name_returns_username(self):
        mock_chats_repo = MagicMock()
        mock_telegram = MagicMock(spec=TelegramService)
        mock_events = MagicMock()

        mock_telegram.get_bot_info = AsyncMock(return_value=MagicMock(username="test_bot"))

        service = ChatsService(mock_chats_repo, mock_telegram, mock_events)
        result = await service._get_bot_name("bot_id_123")
        assert result == "test_bot"

    @pytest.mark.asyncio
    async def test_get_bot_name_returns_invalid_on_error(self):
        mock_chats_repo = MagicMock()
        mock_telegram = MagicMock(spec=TelegramService)
        mock_events = MagicMock()

        mock_telegram.get_bot_info = AsyncMock(side_effect=Exception("API error"))

        service = ChatsService(mock_chats_repo, mock_telegram, mock_events)
        result = await service._get_bot_name("bot_id_123")
        assert result == "Invalid bot identifier"


class TestChatsServiceGetChatName:
    @pytest.mark.asyncio
    async def test_get_chat_name_returns_username(self):
        mock_chats_repo = MagicMock()
        mock_telegram = MagicMock(spec=TelegramService)
        mock_events = MagicMock()

        mock_telegram.get_chat_info = AsyncMock(return_value=MagicMock(username="test_chat", title="Test Chat"))

        service = ChatsService(mock_chats_repo, mock_telegram, mock_events)
        result = await service._get_chat_name("chat_id_123", "bot_id_456")
        assert result == "test_chat"

    @pytest.mark.asyncio
    async def test_get_chat_name_returns_title_when_no_username(self):
        mock_chats_repo = MagicMock()
        mock_telegram = MagicMock(spec=TelegramService)
        mock_events = MagicMock()

        mock_telegram.get_chat_info = AsyncMock(return_value=MagicMock(username=None, title="Test Chat"))

        service = ChatsService(mock_chats_repo, mock_telegram, mock_events)
        result = await service._get_chat_name("chat_id_123", "bot_id_456")
        assert result == "Test Chat"

    @pytest.mark.asyncio
    async def test_get_chat_name_returns_invalid_on_error(self):
        mock_chats_repo = MagicMock()
        mock_telegram = MagicMock(spec=TelegramService)
        mock_events = MagicMock()

        mock_telegram.get_chat_info = AsyncMock(side_effect=Exception("API error"))

        service = ChatsService(mock_chats_repo, mock_telegram, mock_events)
        result = await service._get_chat_name("chat_id_123", "bot_id_456")
        assert result == "Invalid chat identifier"


class TestChatsServiceGetChatsWithErrors:
    @pytest.mark.asyncio
    async def test_get_chats_handles_telegram_errors(self):
        mock_chats_repo = MagicMock()
        mock_telegram = MagicMock(spec=TelegramService)
        mock_events = MagicMock()

        bot = Bot(token="token", enabled=True, hook_enabled=True)
        chat = AllowedChat(chat_id="123", bot=bot)
        mock_chats_repo.get_allowed_chats = AsyncMock(return_value=[chat])

        mock_telegram.get_chat_info = AsyncMock(side_effect=Exception("API error"))
        mock_telegram.get_bot_info = AsyncMock(side_effect=Exception("API error"))

        service = ChatsService(mock_chats_repo, mock_telegram, mock_events)
        result = await service.get_chats()
        assert len(result) == 1
        assert result[0].chat_name == "Invalid chat identifier"
        assert result[0].bot_name == "Invalid bot identifier"
