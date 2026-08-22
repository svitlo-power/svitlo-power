"""Tests for app/services/deye_api/models.py."""
from app.services.deye_api.models import DeyeConfig


class TestDeyeConfig:
    def test_valid_config(self):
        config = DeyeConfig(
            base_url="https://api.example.com",
            app_id="app123",
            app_secret="secret",
            email="test@example.com",
            password="password",
        )
        assert config.base_url == "https://api.example.com"
        assert config.app_id == "app123"
        assert config.app_secret == "secret"
        assert config.email == "test@example.com"
        assert config.password == "password"
        assert config.sync_stations_on_poll is False

    def test_sync_stations_on_poll_true(self):
        config = DeyeConfig(
            base_url="https://api.example.com",
            app_id="app123",
            app_secret="secret",
            email="test@example.com",
            password="password",
            sync_stations_on_poll=True,
        )
        assert config.sync_stations_on_poll is True

    def test_str_masks_secrets(self):
        config = DeyeConfig(
            base_url="https://api.example.com",
            app_id="app123",
            app_secret="secret",
            email="test@example.com",
            password="password",
        )
        result = str(config)
        assert "app_secret='***'" in result
        assert "password='***'" in result
        assert "secret" not in result.replace("app_secret", "")
        assert "password" not in result.replace("password='***'", "")
