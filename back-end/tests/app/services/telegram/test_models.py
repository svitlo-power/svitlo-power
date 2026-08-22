"""Tests for app/services/telegram/models.py."""
from app.services.telegram.models import TelegramConfig, TelegramUserInfo, TelegramChatInfo


class TestTelegramConfig:
    def test_init_with_settings(self):
        mock_settings = MagicMock()
        mock_settings.TG_HOOK_BASE_URL = "https://example.com/hooks"
        config = TelegramConfig(mock_settings)
        assert config.hook_base_url == "https://example.com/hooks"

    def test_str_representation(self):
        mock_settings = MagicMock()
        mock_settings.TG_HOOK_BASE_URL = "https://example.com/hooks"
        config = TelegramConfig(mock_settings)
        result = str(config)
        assert "hook_base_url='https://example.com/hooks'" in result


class TestTelegramUserInfo:
    def test_from_json(self):
        data = {
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
        info = TelegramUserInfo.from_json(data)
        assert info.id == 123456789
        assert info.is_bot is True
        assert info.first_name == "TestBot"
        assert info.username == "test_bot"
        assert info.can_join_groups is True
        assert info.can_read_all_group_messages is False
        assert info.supports_inline_queries is True
        assert info.can_connect_to_business is False
        assert info.has_main_web_app is False

    def test_str_representation(self):
        data = {
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
        info = TelegramUserInfo.from_json(data)
        result = str(info)
        assert "id=123456789" in result
        assert "username='test_bot'" in result


class TestTelegramChatInfo:
    def test_from_json_with_title(self):
        data = {
            "id": 123456789,
            "type": "group",
            "title": "Test Group",
            "username": "test_group",
        }
        info = TelegramChatInfo.from_json(data)
        assert info.id == 123456789
        assert info.type == "group"
        assert info.title == "Test Group"
        assert info.username == "test_group"

    def test_from_json_without_title(self):
        data = {
            "id": 123456789,
            "type": "private",
        }
        info = TelegramChatInfo.from_json(data)
        assert info.id == 123456789
        assert info.type == "private"
        assert info.title is None
        assert info.username is None


# Need to import MagicMock for the TelegramConfig test
from unittest.mock import MagicMock
