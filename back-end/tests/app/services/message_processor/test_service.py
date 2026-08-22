"""Tests for app/services/message_processor/service.py."""
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from beanie import PydanticObjectId

from app.services.message_processor.service import MessageProcessorService
from app.services.interfaces import IMessageGeneratorService, MessageItem
from app.services.telegram.service import TelegramService
from app.repositories import IBotsRepository, IChatsRepository, IMessagesRepository
from shared.models.message import Message
from shared.models.bot import Bot


class TestMessageProcessorServiceInit:
    def test_init_stores_dependencies(self):
        mock_events = MagicMock()
        mock_message_generator = MagicMock(spec=IMessageGeneratorService)
        mock_telegram = MagicMock(spec=TelegramService)
        mock_bots_repo = MagicMock(spec=IBotsRepository)
        mock_chats_repo = MagicMock(spec=IChatsRepository)
        mock_messages_repo = MagicMock(spec=IMessagesRepository)

        service = MessageProcessorService(
            mock_events, mock_message_generator, mock_telegram, mock_bots_repo, mock_chats_repo, mock_messages_repo
        )
        assert service._message_generator is mock_message_generator
        assert service._telegram is mock_telegram
        assert service._bots is mock_bots_repo
        assert service._chats is mock_chats_repo
        assert service._messages is mock_messages_repo


class TestMessageProcessorServicePeriodicSend:
    @pytest.mark.asyncio
    async def test_periodic_send_no_messages(self):
        mock_events = MagicMock()
        mock_message_generator = MagicMock(spec=IMessageGeneratorService)
        mock_telegram = MagicMock(spec=TelegramService)
        mock_bots_repo = MagicMock(spec=IBotsRepository)
        mock_chats_repo = MagicMock(spec=IChatsRepository)
        mock_messages_repo = MagicMock(spec=IMessagesRepository)

        mock_messages_repo.get_messages = AsyncMock(return_value=[])

        service = MessageProcessorService(
            mock_events, mock_message_generator, mock_telegram, mock_bots_repo, mock_chats_repo, mock_messages_repo
        )
        await service.periodic_send()
        mock_message_generator.generate_message.assert_not_called()

    @pytest.mark.asyncio
    async def test_periodic_send_with_message_should_send(self):
        mock_events = MagicMock()
        mock_message_generator = MagicMock(spec=IMessageGeneratorService)
        mock_telegram = MagicMock(spec=TelegramService)
        mock_bots_repo = MagicMock(spec=IBotsRepository)
        mock_chats_repo = MagicMock(spec=IChatsRepository)
        mock_messages_repo = MagicMock(spec=IMessagesRepository)

        bot = Bot(token="token", enabled=True, hook_enabled=True)
        message = Message(name="Test", channel_id="channel", bot=bot, enabled=True, language="en")
        mock_messages_repo.get_messages = AsyncMock(return_value=[message])

        message_item = MessageItem(
            message="Hello",
            timeout=300,
            should_send=True,
            next_send_time=datetime.now(timezone.utc),
            data=None,
        )
        mock_message_generator.generate_message = AsyncMock(return_value=message_item)
        mock_telegram.send_message = AsyncMock()
        mock_messages_repo.set_last_sent = AsyncMock()

        service = MessageProcessorService(
            mock_events, mock_message_generator, mock_telegram, mock_bots_repo, mock_chats_repo, mock_messages_repo
        )
        await service.periodic_send()
        mock_telegram.send_message.assert_called_once()
        mock_messages_repo.set_last_sent.assert_called_once_with(message.id)

    @pytest.mark.asyncio
    async def test_periodic_send_with_message_should_not_send(self):
        mock_events = MagicMock()
        mock_message_generator = MagicMock(spec=IMessageGeneratorService)
        mock_telegram = MagicMock(spec=TelegramService)
        mock_bots_repo = MagicMock(spec=IBotsRepository)
        mock_chats_repo = MagicMock(spec=IChatsRepository)
        mock_messages_repo = MagicMock(spec=IMessagesRepository)

        bot = Bot(token="token", enabled=True, hook_enabled=True)
        message = Message(name="Test", channel_id="channel", bot=bot, enabled=True, language="en")
        mock_messages_repo.get_messages = AsyncMock(return_value=[message])

        message_item = MessageItem(
            message="Hello",
            timeout=300,
            should_send=False,
            next_send_time=datetime.now(timezone.utc),
            data=None,
        )
        mock_message_generator.generate_message = AsyncMock(return_value=message_item)
        mock_telegram.send_message = AsyncMock()

        service = MessageProcessorService(
            mock_events, mock_message_generator, mock_telegram, mock_bots_repo, mock_chats_repo, mock_messages_repo
        )
        await service.periodic_send()
        mock_telegram.send_message.assert_not_called()

    @pytest.mark.asyncio
    async def test_periodic_send_with_none_message_item(self):
        mock_events = MagicMock()
        mock_message_generator = MagicMock(spec=IMessageGeneratorService)
        mock_telegram = MagicMock(spec=TelegramService)
        mock_bots_repo = MagicMock(spec=IBotsRepository)
        mock_chats_repo = MagicMock(spec=IChatsRepository)
        mock_messages_repo = MagicMock(spec=IMessagesRepository)

        bot = Bot(token="token", enabled=True, hook_enabled=True)
        message = Message(name="Test", channel_id="channel", bot=bot, enabled=True, language="en")
        mock_messages_repo.get_messages = AsyncMock(return_value=[message])
        mock_message_generator.generate_message = AsyncMock(return_value=None)

        service = MessageProcessorService(
            mock_events, mock_message_generator, mock_telegram, mock_bots_repo, mock_chats_repo, mock_messages_repo
        )
        await service.periodic_send()
        mock_telegram.send_message.assert_not_called()


class TestMessageProcessorServiceHandleIncomingMessage:
    @pytest.mark.asyncio
    async def test_handle_incoming_message_hook_disabled(self):
        mock_events = MagicMock()
        mock_message_generator = MagicMock(spec=IMessageGeneratorService)
        mock_telegram = MagicMock(spec=TelegramService)
        mock_bots_repo = MagicMock(spec=IBotsRepository)
        mock_chats_repo = MagicMock(spec=IChatsRepository)
        mock_messages_repo = MagicMock(spec=IMessagesRepository)

        mock_bots_repo.get_is_hook_enabled = AsyncMock(return_value=False)

        service = MessageProcessorService(
            mock_events, mock_message_generator, mock_telegram, mock_bots_repo, mock_chats_repo, mock_messages_repo
        )
        await service.handle_incoming_message(PydanticObjectId(), {"message": {"chat": {"id": "123"}, "text": "hello"}})
        mock_telegram.send_message.assert_not_called()

    @pytest.mark.asyncio
    async def test_handle_incoming_message_chat_not_allowed(self):
        mock_events = MagicMock()
        mock_message_generator = MagicMock(spec=IMessageGeneratorService)
        mock_telegram = MagicMock(spec=TelegramService)
        mock_bots_repo = MagicMock(spec=IBotsRepository)
        mock_chats_repo = MagicMock(spec=IChatsRepository)
        mock_messages_repo = MagicMock(spec=IMessagesRepository)

        mock_bots_repo.get_is_hook_enabled = AsyncMock(return_value=True)
        mock_chats_repo.get_is_chat_allowed = AsyncMock(return_value=False)
        mock_chats_repo.add_chat_request = AsyncMock()

        service = MessageProcessorService(
            mock_events, mock_message_generator, mock_telegram, mock_bots_repo, mock_chats_repo, mock_messages_repo
        )
        await service.handle_incoming_message(PydanticObjectId(), {"message": {"chat": {"id": "123"}, "text": "hello"}})
        mock_chats_repo.add_chat_request.assert_called_once()
        mock_telegram.send_message.assert_not_called()

    @pytest.mark.asyncio
    async def test_handle_incoming_message_chat_allowed(self):
        mock_events = MagicMock()
        mock_message_generator = MagicMock(spec=IMessageGeneratorService)
        mock_telegram = MagicMock(spec=TelegramService)
        mock_bots_repo = MagicMock(spec=IBotsRepository)
        mock_chats_repo = MagicMock(spec=IChatsRepository)
        mock_messages_repo = MagicMock(spec=IMessagesRepository)

        mock_bots_repo.get_is_hook_enabled = AsyncMock(return_value=True)
        mock_chats_repo.get_is_chat_allowed = AsyncMock(return_value=True)
        mock_telegram.send_message = AsyncMock()

        service = MessageProcessorService(
            mock_events, mock_message_generator, mock_telegram, mock_bots_repo, mock_chats_repo, mock_messages_repo
        )
        await service.handle_incoming_message(PydanticObjectId(), {"message": {"chat": {"id": "123"}, "text": "hello"}})
        mock_telegram.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_incoming_message_no_message_key(self):
        mock_events = MagicMock()
        mock_message_generator = MagicMock(spec=IMessageGeneratorService)
        mock_telegram = MagicMock(spec=TelegramService)
        mock_bots_repo = MagicMock(spec=IBotsRepository)
        mock_chats_repo = MagicMock(spec=IChatsRepository)
        mock_messages_repo = MagicMock(spec=IMessagesRepository)

        service = MessageProcessorService(
            mock_events, mock_message_generator, mock_telegram, mock_bots_repo, mock_chats_repo, mock_messages_repo
        )
        await service.handle_incoming_message(PydanticObjectId(), {"other": "data"})
        mock_telegram.send_message.assert_not_called()

    @pytest.mark.asyncio
    async def test_send_message_exception_handled(self):
        """Test _send_message handles exceptions."""
        mock_events = MagicMock()
        mock_message_generator = MagicMock(spec=IMessageGeneratorService)
        mock_telegram = MagicMock(spec=TelegramService)
        mock_bots_repo = MagicMock(spec=IBotsRepository)
        mock_chats_repo = MagicMock(spec=IChatsRepository)
        mock_messages_repo = MagicMock(spec=IMessagesRepository)

        mock_telegram.send_message = AsyncMock(side_effect=Exception("Telegram error"))
        mock_messages_repo.set_last_sent = AsyncMock()

        service = MessageProcessorService(
            mock_events, mock_message_generator, mock_telegram, mock_bots_repo, mock_chats_repo, mock_messages_repo
        )

        bot = Bot(token="token", enabled=True, hook_enabled=True)
        message = Message(name="Test", channel_id="channel", bot=bot, enabled=True, language="en")

        # Should not raise exception
        await service._send_message(message, "Hello")
        mock_telegram.send_message.assert_called_once()
        mock_messages_repo.set_last_sent.assert_not_called()  # Not called due to exception

    @pytest.mark.asyncio
    async def test_periodic_send_exception_handled(self):
        """Test periodic_send handles exceptions from generate_message."""
        mock_events = MagicMock()
        mock_message_generator = MagicMock(spec=IMessageGeneratorService)
        mock_telegram = MagicMock(spec=TelegramService)
        mock_bots_repo = MagicMock(spec=IBotsRepository)
        mock_chats_repo = MagicMock(spec=IChatsRepository)
        mock_messages_repo = MagicMock(spec=IMessagesRepository)

        bot = Bot(token="token", enabled=True, hook_enabled=True)
        message = Message(name="Test", channel_id="channel", bot=bot, enabled=True, language="en")
        mock_messages_repo.get_messages = AsyncMock(return_value=[message])
        mock_message_generator.generate_message = AsyncMock(side_effect=Exception("Generator error"))

        service = MessageProcessorService(
            mock_events, mock_message_generator, mock_telegram, mock_bots_repo, mock_chats_repo, mock_messages_repo
        )
        await service.periodic_send()
        mock_message_generator.generate_message.assert_called_once()
        mock_telegram.send_message.assert_not_called()

    @pytest.mark.asyncio
    async def test_periodic_send_send_message_exception_handled(self):
        """Test periodic_send handles exceptions from _send_message."""
        mock_events = MagicMock()
        mock_message_generator = MagicMock(spec=IMessageGeneratorService)
        mock_telegram = MagicMock(spec=TelegramService)
        mock_bots_repo = MagicMock(spec=IBotsRepository)
        mock_chats_repo = MagicMock(spec=IChatsRepository)
        mock_messages_repo = MagicMock(spec=IMessagesRepository)

        bot = Bot(token="token", enabled=True, hook_enabled=True)
        message = Message(name="Test", channel_id="channel", bot=bot, enabled=True, language="en")
        mock_messages_repo.get_messages = AsyncMock(return_value=[message])

        message_item = MessageItem(
            message="Hello",
            timeout=300,
            should_send=True,
            next_send_time=datetime.now(timezone.utc),
            data=None,
        )
        mock_message_generator.generate_message = AsyncMock(return_value=message_item)
        mock_telegram.send_message = AsyncMock(side_effect=Exception("Send error"))
        mock_messages_repo.set_last_sent = AsyncMock()

        service = MessageProcessorService(
            mock_events, mock_message_generator, mock_telegram, mock_bots_repo, mock_chats_repo, mock_messages_repo
        )
        await service.periodic_send()
        mock_telegram.send_message.assert_called_once()
        mock_messages_repo.set_last_sent.assert_not_called()
