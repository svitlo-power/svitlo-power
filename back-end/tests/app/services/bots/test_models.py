"""Tests for app/services/bots/models.py."""
from datetime import datetime
from unittest.mock import MagicMock

import pytest

from app.services.bots.models import BotConfig, MessageItem
from app.settings import Settings


class TestBotConfig:
    def test_bot_config_str(self):
        """Test BotConfig __str__ method."""
        mock_settings = MagicMock(spec=Settings)
        mock_settings.BOT_TIMEZONE = "utc"
        config = BotConfig(mock_settings)
        result = str(config)
        assert "BotConfig" in result
        assert "utc" in result


class TestMessageItem:
    def test_message_item_creation(self):
        """Test MessageItem dataclass creation."""
        now = datetime.now()
        item = MessageItem(
            message="Test message",
            timeout=300,
            should_send=True,
            next_send_time=now,
        )
        assert item.message == "Test message"
        assert item.timeout == 300
        assert item.should_send is True
        assert item.next_send_time == now
