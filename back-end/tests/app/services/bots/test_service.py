"""Tests for app/services/bots/service.py."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from beanie import PydanticObjectId

from app.services.bots.service import BotsService
from app.services.telegram.service import TelegramService
from app.models.api import BotResponse, CreateBotRequest, UpdateBotRequest
from shared.models.bot import Bot


class TestBotsServiceInit:
    def test_init_stores_dependencies(self):
        mock_telegram = MagicMock(spec=TelegramService)
        mock_bots_repo = MagicMock()
        mock_events = MagicMock()

        service = BotsService(mock_telegram, mock_bots_repo, mock_events)
        assert service._telegram is mock_telegram
        assert service._bots is mock_bots_repo


class TestBotsServiceGetEnabledBots:
    @pytest.mark.asyncio
    async def test_get_enabled_bots_delegates_to_repository(self):
        mock_telegram = MagicMock(spec=TelegramService)
        mock_bots_repo = MagicMock()
        mock_events = MagicMock()

        bots = [Bot(token="token1", enabled=True, hook_enabled=True)]
        mock_bots_repo.get_bots = AsyncMock(return_value=bots)

        service = BotsService(mock_telegram, mock_bots_repo, mock_events)
        result = await service.get_enabled_bots()
        assert result == bots
        mock_bots_repo.get_bots.assert_called_once_with(False)


class TestBotsServiceGetBots:
    @pytest.mark.asyncio
    async def test_get_bots_returns_response_list(self):
        mock_telegram = MagicMock(spec=TelegramService)
        mock_bots_repo = MagicMock()
        mock_events = MagicMock()

        bot = Bot(token="token1", enabled=True, hook_enabled=True)
        mock_bots_repo.get_bots = AsyncMock(return_value=[bot])

        mock_telegram.get_bot_info = AsyncMock(return_value=MagicMock(username="test_bot"))

        service = BotsService(mock_telegram, mock_bots_repo, mock_events)
        result = await service.get_bots()
        assert len(result) == 1
        assert isinstance(result[0], BotResponse)
        assert result[0].name == "test_bot"

    @pytest.mark.asyncio
    async def test_get_bots_handles_telegram_error(self):
        mock_telegram = MagicMock(spec=TelegramService)
        mock_bots_repo = MagicMock()
        mock_events = MagicMock()

        bot = Bot(token="token1", enabled=True, hook_enabled=True)
        mock_bots_repo.get_bots = AsyncMock(return_value=[bot])

        mock_telegram.get_bot_info = AsyncMock(side_effect=Exception("API error"))

        service = BotsService(mock_telegram, mock_bots_repo, mock_events)
        result = await service.get_bots()
        assert len(result) == 1
        assert result[0].name == "Invalid bot token"


class TestBotsServiceGetBot:
    @pytest.mark.asyncio
    async def test_get_bot_delegates_to_repository(self):
        mock_telegram = MagicMock(spec=TelegramService)
        mock_bots_repo = MagicMock()
        mock_events = MagicMock()

        bot = Bot(token="token1", enabled=True, hook_enabled=True)
        mock_bots_repo.get_bot = AsyncMock(return_value=bot)

        service = BotsService(mock_telegram, mock_bots_repo, mock_events)
        result = await service.get_bot(PydanticObjectId())
        assert result == bot


class TestBotsServiceCreateBot:
    @pytest.mark.asyncio
    async def test_create_bot_enabled_registers_with_telegram(self):
        mock_telegram = MagicMock(spec=TelegramService)
        mock_bots_repo = MagicMock()
        mock_events = MagicMock()

        bot = Bot(token="token1", enabled=True, hook_enabled=True)
        mock_bots_repo.create_bot = AsyncMock(return_value=bot)
        mock_telegram.add_bot = AsyncMock()

        service = BotsService(mock_telegram, mock_bots_repo, mock_events)
        dto = CreateBotRequest(enabled=True, hookEnabled=True, token="token1")
        result = await service.create_bot(dto)
        assert result == bot
        mock_telegram.add_bot.assert_called_once_with(bot.id, bot.token, bot.hook_enabled)

    @pytest.mark.asyncio
    async def test_create_bot_disabled_does_not_register(self):
        mock_telegram = MagicMock(spec=TelegramService)
        mock_bots_repo = MagicMock()
        mock_events = MagicMock()

        bot = Bot(token="token1", enabled=False, hook_enabled=False)
        mock_bots_repo.create_bot = AsyncMock(return_value=bot)
        mock_telegram.add_bot = AsyncMock()

        service = BotsService(mock_telegram, mock_bots_repo, mock_events)
        dto = CreateBotRequest(enabled=False, hookEnabled=False, token="token1")
        result = await service.create_bot(dto)
        assert result == bot
        mock_telegram.add_bot.assert_not_called()


class TestBotsServiceUpdateBot:
    @pytest.mark.asyncio
    async def test_update_bot_enabled_registers_with_telegram(self):
        mock_telegram = MagicMock(spec=TelegramService)
        mock_bots_repo = MagicMock()
        mock_events = MagicMock()

        bot = Bot(token="token1", enabled=True, hook_enabled=True)
        mock_bots_repo.update_bot = AsyncMock(return_value=bot)
        mock_telegram.add_bot = AsyncMock()

        service = BotsService(mock_telegram, mock_bots_repo, mock_events)
        dto = UpdateBotRequest(enabled=True, hookEnabled=True)
        result = await service.update_bot(PydanticObjectId(), dto)
        assert result == bot
        mock_telegram.add_bot.assert_called_once_with(bot.id, bot.token, bot.hook_enabled)

    @pytest.mark.asyncio
    async def test_update_bot_disabled_removes_from_telegram(self):
        mock_telegram = MagicMock(spec=TelegramService)
        mock_bots_repo = MagicMock()
        mock_events = MagicMock()

        bot = Bot(token="token1", enabled=False, hook_enabled=False)
        mock_bots_repo.update_bot = AsyncMock(return_value=bot)
        mock_telegram.remove_bot = AsyncMock()

        service = BotsService(mock_telegram, mock_bots_repo, mock_events)
        dto = UpdateBotRequest(enabled=False, hookEnabled=False)
        result = await service.update_bot(PydanticObjectId(), dto)
        assert result == bot
        mock_telegram.remove_bot.assert_called_once_with(bot.id)
