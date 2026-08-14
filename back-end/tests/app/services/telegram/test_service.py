"""Tests for app/services/telegram/service.py."""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from beanie import PydanticObjectId

from app.services.telegram.service import TelegramService
from app.services.telegram.models import TelegramConfig, TelegramUserInfo, TelegramChatInfo
import aiohttp


class TestTelegramServiceInit:
    def test_init_with_config_and_no_session(self):
        mock_settings = MagicMock()
        mock_settings.TG_HOOK_BASE_URL = "https://example.com/hooks"
        config = TelegramConfig(mock_settings)

        with patch("app.services.telegram.service.aiohttp.ClientSession") as mock_session_cls:
            service = TelegramService(config)
            assert service._hook_base_url == "https://example.com/hooks"
            assert service._bot_tokens == {}
            assert service._session is not None

    def test_init_with_provided_session(self):
        mock_settings = MagicMock()
        mock_settings.TG_HOOK_BASE_URL = "https://example.com/hooks"
        config = TelegramConfig(mock_settings)
        mock_session = MagicMock()

        service = TelegramService(config, session=mock_session)
        assert service._session is mock_session


class TestTelegramServiceShutdown:
    @pytest.mark.asyncio
    async def test_shutdown_closes_session(self):
        mock_settings = MagicMock()
        mock_settings.TG_HOOK_BASE_URL = "https://example.com/hooks"
        config = TelegramConfig(mock_settings)
        mock_session = MagicMock()
        mock_session.close = AsyncMock()

        service = TelegramService(config, session=mock_session)
        await service.shutdown()
        mock_session.close.assert_called_once()


class TestTelegramServiceGetMethodUrl:
    def test_get_method_url(self):
        mock_settings = MagicMock()
        mock_settings.TG_HOOK_BASE_URL = "https://example.com/hooks"
        config = TelegramConfig(mock_settings)
        mock_session = MagicMock()

        service = TelegramService(config, session=mock_session)
        url = service._get_method_url("test-token", "sendMessage")
        assert url == "https://api.telegram.org/bottest-token/sendMessage"


class TestTelegramServiceAddBot:
    @pytest.mark.asyncio
    async def test_add_bot_stores_token(self):
        mock_settings = MagicMock()
        mock_settings.TG_HOOK_BASE_URL = "https://example.com/hooks"
        config = TelegramConfig(mock_settings)
        mock_session = MagicMock()

        service = TelegramService(config, session=mock_session)
        bot_id = PydanticObjectId()

        service.register_hook = AsyncMock(return_value=True)
        service.unregister_hook = AsyncMock(return_value=True)

        await service.add_bot(bot_id, "test-token", enable_hook=True)
        assert service._bot_tokens[bot_id] == "test-token"
        service.register_hook.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_bot_without_hook(self):
        mock_settings = MagicMock()
        mock_settings.TG_HOOK_BASE_URL = "https://example.com/hooks"
        config = TelegramConfig(mock_settings)
        mock_session = MagicMock()

        service = TelegramService(config, session=mock_session)
        bot_id = PydanticObjectId()

        service.register_hook = AsyncMock(return_value=True)
        service.unregister_hook = AsyncMock(return_value=True)

        await service.add_bot(bot_id, "test-token", enable_hook=False)
        assert service._bot_tokens[bot_id] == "test-token"
        service.unregister_hook.assert_called_once()


class TestTelegramServiceRemoveBot:
    @pytest.mark.asyncio
    async def test_remove_bot_not_in_tokens(self):
        mock_settings = MagicMock()
        mock_settings.TG_HOOK_BASE_URL = "https://example.com/hooks"
        config = TelegramConfig(mock_settings)
        mock_session = MagicMock()

        service = TelegramService(config, session=mock_session)
        bot_id = PydanticObjectId()

        service.unregister_hook = AsyncMock(return_value=True)
        await service.remove_bot(bot_id)
        service.unregister_hook.assert_not_called()

    @pytest.mark.asyncio
    async def test_remove_bot_in_tokens(self):
        mock_settings = MagicMock()
        mock_settings.TG_HOOK_BASE_URL = "https://example.com/hooks"
        config = TelegramConfig(mock_settings)
        mock_session = MagicMock()

        service = TelegramService(config, session=mock_session)
        bot_id = PydanticObjectId()
        service._bot_tokens[bot_id] = "test-token"

        service.unregister_hook = AsyncMock(return_value=True)
        await service.remove_bot(bot_id)
        assert bot_id not in service._bot_tokens
        service.unregister_hook.assert_called_once_with("test-token")


class TestTelegramServiceRegisterHook:
    @pytest.mark.asyncio
    async def test_register_hook_success(self):
        mock_settings = MagicMock()
        mock_settings.TG_HOOK_BASE_URL = "https://example.com/hooks"
        config = TelegramConfig(mock_settings)
        mock_session = MagicMock()

        service = TelegramService(config, session=mock_session)

        mock_response = MagicMock()
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        mock_response.raise_for_status = MagicMock()
        mock_response.json = AsyncMock(return_value={"ok": True, "result": True})

        mock_session.post = MagicMock(return_value=mock_response)

        result = await service.register_hook("test-token", "https://example.com/hook")
        assert result is True

    @pytest.mark.asyncio
    async def test_register_hook_failure(self):
        mock_settings = MagicMock()
        mock_settings.TG_HOOK_BASE_URL = "https://example.com/hooks"
        config = TelegramConfig(mock_settings)
        mock_session = MagicMock()

        service = TelegramService(config, session=mock_session)

        mock_response = MagicMock()
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        mock_response.raise_for_status = MagicMock(side_effect=Exception("HTTP error"))

        mock_session.post = MagicMock(return_value=mock_response)

        result = await service.register_hook("test-token", "https://example.com/hook")
        assert result is None


class TestTelegramServiceUnregisterHook:
    @pytest.mark.asyncio
    async def test_unregister_hook_success(self):
        mock_settings = MagicMock()
        mock_settings.TG_HOOK_BASE_URL = "https://example.com/hooks"
        config = TelegramConfig(mock_settings)
        mock_session = MagicMock()

        service = TelegramService(config, session=mock_session)

        mock_response = MagicMock()
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        mock_response.raise_for_status = MagicMock()
        mock_response.json = AsyncMock(return_value={"ok": True, "result": True})

        mock_session.post = MagicMock(return_value=mock_response)

        result = await service.unregister_hook("test-token")
        assert result is True


class TestTelegramServiceSendMessage:
    @pytest.mark.asyncio
    async def test_send_message_success(self):
        mock_settings = MagicMock()
        mock_settings.TG_HOOK_BASE_URL = "https://example.com/hooks"
        config = TelegramConfig(mock_settings)
        mock_session = MagicMock()

        service = TelegramService(config, session=mock_session)
        bot_id = PydanticObjectId()
        service._bot_tokens[bot_id] = "test-token"

        mock_response = MagicMock()
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        mock_response.raise_for_status = MagicMock()

        mock_session.post = MagicMock(return_value=mock_response)

        await service.send_message(bot_id, "chat123", "Hello")
        mock_session.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_message_failure_returns_none(self):
        mock_settings = MagicMock()
        mock_settings.TG_HOOK_BASE_URL = "https://example.com/hooks"
        config = TelegramConfig(mock_settings)
        mock_session = MagicMock()

        service = TelegramService(config, session=mock_session)
        bot_id = PydanticObjectId()
        service._bot_tokens[bot_id] = "test-token"

        mock_response = MagicMock()
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        mock_response.raise_for_status = MagicMock(side_effect=Exception("HTTP error"))

        mock_session.post = MagicMock(return_value=mock_response)

        result = await service.send_message(bot_id, "chat123", "Hello")
        assert result is None


class TestTelegramServiceGetBotInfo:
    @pytest.mark.asyncio
    async def test_get_bot_info_success(self):
        mock_settings = MagicMock()
        mock_settings.TG_HOOK_BASE_URL = "https://example.com/hooks"
        config = TelegramConfig(mock_settings)
        mock_session = MagicMock()

        service = TelegramService(config, session=mock_session)
        bot_id = PydanticObjectId()
        service._bot_tokens[bot_id] = "test-token"

        mock_response = MagicMock()
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        mock_response.raise_for_status = MagicMock()
        mock_response.json = AsyncMock(return_value={
            "ok": True,
            "result": {
                "id": 123456789,
                "is_bot": True,
                "first_name": "TestBot",
                "username": "test_bot",
                "can_join_groups": True,
                "can_read_all_group_messages": False,
                "supports_inline_queries": True,
                "can_connect_to_business": False,
                "has_main_web_app": False,
            }
        })

        mock_session.post = MagicMock(return_value=mock_response)

        result = await service.get_bot_info(bot_id)
        assert isinstance(result, TelegramUserInfo)
        assert result.username == "test_bot"

    @pytest.mark.asyncio
    async def test_get_bot_info_failure_returns_none(self):
        mock_settings = MagicMock()
        mock_settings.TG_HOOK_BASE_URL = "https://example.com/hooks"
        config = TelegramConfig(mock_settings)
        mock_session = MagicMock()

        service = TelegramService(config, session=mock_session)
        bot_id = PydanticObjectId()
        service._bot_tokens[bot_id] = "test-token"

        mock_response = MagicMock()
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        mock_response.raise_for_status = MagicMock(side_effect=Exception("HTTP error"))

        mock_session.post = MagicMock(return_value=mock_response)

        result = await service.get_bot_info(bot_id)
        assert result is None


class TestTelegramServiceGetChatInfo:
    @pytest.mark.asyncio
    async def test_get_chat_info_success(self):
        mock_settings = MagicMock()
        mock_settings.TG_HOOK_BASE_URL = "https://example.com/hooks"
        config = TelegramConfig(mock_settings)
        mock_session = MagicMock()

        service = TelegramService(config, session=mock_session)
        bot_id = PydanticObjectId()
        service._bot_tokens[bot_id] = "test-token"

        mock_response = MagicMock()
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        mock_response.raise_for_status = MagicMock()
        mock_response.json = AsyncMock(return_value={
            "ok": True,
            "result": {
                "id": 123456789,
                "type": "group",
                "title": "Test Group",
                "username": "test_group",
            }
        })

        mock_session.post = MagicMock(return_value=mock_response)

        result = await service.get_chat_info("chat123", bot_id)
        assert isinstance(result, TelegramChatInfo)
        assert result.title == "Test Group"

    @pytest.mark.asyncio
    async def test_get_chat_info_failure_returns_none(self):
        mock_settings = MagicMock()
        mock_settings.TG_HOOK_BASE_URL = "https://example.com/hooks"
        config = TelegramConfig(mock_settings)
        mock_session = MagicMock()

        service = TelegramService(config, session=mock_session)
        bot_id = PydanticObjectId()
        service._bot_tokens[bot_id] = "test-token"

        mock_response = MagicMock()
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        mock_response.raise_for_status = MagicMock(side_effect=Exception("HTTP error"))

        mock_session.post = MagicMock(return_value=mock_response)

        result = await service.get_chat_info("chat123", bot_id)
        assert result is None


class TestTelegramServiceClientResponseError:
    """Tests for aiohttp.ClientResponseError exception paths."""

    @pytest.mark.asyncio
    async def test_register_hook_client_response_error(self):
        """Test register_hook handles aiohttp.ClientResponseError."""
        mock_settings = MagicMock()
        mock_settings.TG_HOOK_BASE_URL = "https://example.com/hooks"
        config = TelegramConfig(mock_settings)
        mock_session = MagicMock()

        service = TelegramService(config, session=mock_session)

        mock_response = MagicMock()
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        mock_response.raise_for_status = MagicMock(side_effect=aiohttp.ClientResponseError(
            request_info=MagicMock(),
            history=(),
            status=400,
            message="Bad Request",
        ))

        mock_session.post = MagicMock(return_value=mock_response)

        result = await service.register_hook("test-token", "https://example.com/hook")
        assert result is None

    @pytest.mark.asyncio
    async def test_unregister_hook_client_response_error(self):
        """Test unregister_hook handles aiohttp.ClientResponseError."""
        mock_settings = MagicMock()
        mock_settings.TG_HOOK_BASE_URL = "https://example.com/hooks"
        config = TelegramConfig(mock_settings)
        mock_session = MagicMock()

        service = TelegramService(config, session=mock_session)

        mock_response = MagicMock()
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        mock_response.raise_for_status = MagicMock(side_effect=aiohttp.ClientResponseError(
            request_info=MagicMock(),
            history=(),
            status=400,
            message="Bad Request",
        ))

        mock_session.post = MagicMock(return_value=mock_response)

        result = await service.unregister_hook("test-token")
        assert result is None

    @pytest.mark.asyncio
    async def test_send_message_client_response_error(self):
        """Test send_message handles aiohttp.ClientResponseError."""
        mock_settings = MagicMock()
        mock_settings.TG_HOOK_BASE_URL = "https://example.com/hooks"
        config = TelegramConfig(mock_settings)
        mock_session = MagicMock()

        service = TelegramService(config, session=mock_session)
        bot_id = PydanticObjectId()
        service._bot_tokens[bot_id] = "test-token"

        mock_response = MagicMock()
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        mock_response.raise_for_status = MagicMock(side_effect=aiohttp.ClientResponseError(
            request_info=MagicMock(),
            history=(),
            status=400,
            message="Bad Request",
        ))

        mock_session.post = MagicMock(return_value=mock_response)

        result = await service.send_message(bot_id, "chat123", "Hello")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_bot_info_client_response_error(self):
        """Test get_bot_info handles aiohttp.ClientResponseError."""
        mock_settings = MagicMock()
        mock_settings.TG_HOOK_BASE_URL = "https://example.com/hooks"
        config = TelegramConfig(mock_settings)
        mock_session = MagicMock()

        service = TelegramService(config, session=mock_session)
        bot_id = PydanticObjectId()
        service._bot_tokens[bot_id] = "test-token"

        mock_response = MagicMock()
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        mock_response.raise_for_status = MagicMock(side_effect=aiohttp.ClientResponseError(
            request_info=MagicMock(),
            history=(),
            status=400,
            message="Bad Request",
        ))

        mock_session.post = MagicMock(return_value=mock_response)

        result = await service.get_bot_info(bot_id)
        assert result is None

    @pytest.mark.asyncio
    async def test_get_chat_info_client_response_error(self):
        """Test get_chat_info handles aiohttp.ClientResponseError."""
        mock_settings = MagicMock()
        mock_settings.TG_HOOK_BASE_URL = "https://example.com/hooks"
        config = TelegramConfig(mock_settings)
        mock_session = MagicMock()

        service = TelegramService(config, session=mock_session)
        bot_id = PydanticObjectId()
        service._bot_tokens[bot_id] = "test-token"

        mock_response = MagicMock()
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        mock_response.raise_for_status = MagicMock(side_effect=aiohttp.ClientResponseError(
            request_info=MagicMock(),
            history=(),
            status=400,
            message="Bad Request",
        ))

        mock_session.post = MagicMock(return_value=mock_response)

        result = await service.get_chat_info("chat123", bot_id)
        assert result is None

    @pytest.mark.asyncio
    async def test_get_bot_info_no_result(self):
        """Test get_bot_info returns None when response has no result."""
        mock_settings = MagicMock()
        mock_settings.TG_HOOK_BASE_URL = "https://example.com/hooks"
        config = TelegramConfig(mock_settings)
        mock_session = MagicMock()

        service = TelegramService(config, session=mock_session)
        bot_id = PydanticObjectId()
        service._bot_tokens[bot_id] = "test-token"

        mock_response = MagicMock()
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        mock_response.raise_for_status = MagicMock()
        mock_response.json = AsyncMock(return_value={"ok": True, "result": None})

        mock_session.post = MagicMock(return_value=mock_response)

        result = await service.get_bot_info(bot_id)
        assert result is None

    @pytest.mark.asyncio
    async def test_get_chat_info_no_result(self):
        """Test get_chat_info returns None when response has no result."""
        mock_settings = MagicMock()
        mock_settings.TG_HOOK_BASE_URL = "https://example.com/hooks"
        config = TelegramConfig(mock_settings)
        mock_session = MagicMock()

        service = TelegramService(config, session=mock_session)
        bot_id = PydanticObjectId()
        service._bot_tokens[bot_id] = "test-token"

        mock_response = MagicMock()
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        mock_response.raise_for_status = MagicMock()
        mock_response.json = AsyncMock(return_value={"ok": True, "result": None})

        mock_session.post = MagicMock(return_value=mock_response)

        result = await service.get_chat_info("chat123", bot_id)
        assert result is None

    @pytest.mark.asyncio
    async def test_register_hook_no_result(self):
        """Test register_hook returns None when response has no result."""
        mock_settings = MagicMock()
        mock_settings.TG_HOOK_BASE_URL = "https://example.com/hooks"
        config = TelegramConfig(mock_settings)
        mock_session = MagicMock()

        service = TelegramService(config, session=mock_session)

        mock_response = MagicMock()
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        mock_response.raise_for_status = MagicMock()
        mock_response.json = AsyncMock(return_value={"ok": True, "result": False})

        mock_session.post = MagicMock(return_value=mock_response)

        result = await service.register_hook("test-token", "https://example.com/hook")
        assert result is False

    @pytest.mark.asyncio
    async def test_register_hook_generic_exception(self):
        """Test register_hook handles generic Exception."""
        mock_settings = MagicMock()
        mock_settings.TG_HOOK_BASE_URL = "https://example.com/hooks"
        config = TelegramConfig(mock_settings)
        mock_session = MagicMock()

        service = TelegramService(config, session=mock_session)

        mock_response = MagicMock()
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        mock_response.raise_for_status = MagicMock(side_effect=Exception("Network error"))

        mock_session.post = MagicMock(return_value=mock_response)

        result = await service.register_hook("test-token", "https://example.com/hook")
        assert result is None

    @pytest.mark.asyncio
    async def test_register_hook_success(self):
        """Test register_hook successful path (covers lines 52, 53)."""
        mock_settings = MagicMock()
        mock_settings.TG_HOOK_BASE_URL = "https://example.com/hooks"
        config = TelegramConfig(mock_settings)
        mock_session = MagicMock()

        service = TelegramService(config, session=mock_session)

        mock_response = MagicMock()
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        mock_response.raise_for_status = MagicMock()
        mock_response.json = AsyncMock(return_value={"ok": True, "result": True})

        mock_session.post = MagicMock(return_value=mock_response)

        result = await service.register_hook("test-token", "https://example.com/hook")
        assert result is True

    @pytest.mark.asyncio
    async def test_unregister_hook_success(self):
        """Test unregister_hook successful path (covers lines 66, 67)."""
        mock_settings = MagicMock()
        mock_settings.TG_HOOK_BASE_URL = "https://example.com/hooks"
        config = TelegramConfig(mock_settings)
        mock_session = MagicMock()

        service = TelegramService(config, session=mock_session)

        mock_response = MagicMock()
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        mock_response.raise_for_status = MagicMock()
        mock_response.json = AsyncMock(return_value={"ok": True, "result": True})

        mock_session.post = MagicMock(return_value=mock_response)

        result = await service.unregister_hook("test-token")
        assert result is True

    @pytest.mark.asyncio
    async def test_send_message_success(self):
        """Test send_message successful path (covers lines 84-88)."""
        mock_settings = MagicMock()
        mock_settings.TG_HOOK_BASE_URL = "https://example.com/hooks"
        config = TelegramConfig(mock_settings)
        mock_session = MagicMock()

        service = TelegramService(config, session=mock_session)
        bot_id = PydanticObjectId()
        service._bot_tokens[bot_id] = "test-token"

        mock_response = MagicMock()
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        mock_response.raise_for_status = MagicMock()

        mock_session.post = MagicMock(return_value=mock_response)

        result = await service.send_message(bot_id, "chat123", "Hello")
        assert result is None  # send_message returns None on success

    @pytest.mark.asyncio
    async def test_get_bot_info_success(self):
        """Test get_bot_info successful path (covers line 102)."""
        mock_settings = MagicMock()
        mock_settings.TG_HOOK_BASE_URL = "https://example.com/hooks"
        config = TelegramConfig(mock_settings)
        mock_session = MagicMock()

        service = TelegramService(config, session=mock_session)
        bot_id = PydanticObjectId()
        service._bot_tokens[bot_id] = "test-token"

        mock_response = MagicMock()
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        mock_response.raise_for_status = MagicMock()
        mock_response.json = AsyncMock(return_value={
            "ok": True,
            "result": {
                "id": 123456789,
                "is_bot": True,
                "first_name": "TestBot",
                "username": "test_bot",
                "can_join_groups": True,
                "can_read_all_group_messages": False,
                "supports_inline_queries": True,
                "can_connect_to_business": False,
                "has_main_web_app": False,
            }
        })

        mock_session.post = MagicMock(return_value=mock_response)

        result = await service.get_bot_info(bot_id)
        assert result is not None
        assert result.username == "test_bot"

    @pytest.mark.asyncio
    async def test_get_chat_info_success(self):
        """Test get_chat_info successful path (covers line 121)."""
        mock_settings = MagicMock()
        mock_settings.TG_HOOK_BASE_URL = "https://example.com/hooks"
        config = TelegramConfig(mock_settings)
        mock_session = MagicMock()

        service = TelegramService(config, session=mock_session)
        bot_id = PydanticObjectId()
        service._bot_tokens[bot_id] = "test-token"

        mock_response = MagicMock()
        mock_response.__aenter__ = AsyncMock(return_value=mock_response)
        mock_response.__aexit__ = AsyncMock(return_value=None)
        mock_response.raise_for_status = MagicMock()
        mock_response.json = AsyncMock(return_value={
            "ok": True,
            "result": {
                "id": 123456789,
                "type": "group",
                "title": "Test Group",
                "username": "test_group",
            }
        })

        mock_session.post = MagicMock(return_value=mock_response)

        result = await service.get_chat_info("chat123", bot_id)
        assert result is not None
        assert result.title == "Test Group"
