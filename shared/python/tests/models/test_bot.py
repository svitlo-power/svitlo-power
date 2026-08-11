"""Tests for shared/models/bot.py."""
from shared.models.bot import Bot


class TestBot:
    def test_bot_has_token_field(self):
        assert "token" in Bot.model_fields

    def test_bot_token_defaults_none(self):
        assert Bot.model_fields["token"].default is None

    def test_bot_has_enabled_field(self):
        assert "enabled" in Bot.model_fields

    def test_bot_enabled_defaults_true(self):
        assert Bot.model_fields["enabled"].default is True

    def test_bot_has_hook_enabled_field(self):
        assert "hook_enabled" in Bot.model_fields

    def test_bot_hook_enabled_defaults_true(self):
        assert Bot.model_fields["hook_enabled"].default is True

    def test_bot_settings_name(self):
        assert Bot.model_config.get("name") == "bots" or Bot.Settings.name == "bots"
