from unittest.mock import AsyncMock

import pytest

from shared.models.localizable_value import LocalizableValue
from shared.models.system_setting import SystemSetting
from shared.services.settings.service import SettingsService


def test_system_setting_accepts_localizable_text_value():
    setting = SystemSetting(
        key="dashboard_title",
        label="Dashboard title",
        description="Localized dashboard title",
        setting_type="localizable_text",
        default_value={"en": "Dashboard", "uk": "Панель керування"},
        value={"en": "My dashboard", "uk": "Моя панель"},
        category="dashboard",
    )

    assert isinstance(setting.default_value, LocalizableValue)
    assert isinstance(setting.value, LocalizableValue)
    assert setting.value.root == {"en": "My dashboard", "uk": "Моя панель"}


@pytest.mark.asyncio
async def test_get_localizable_text_returns_localizable_value():
    service = SettingsService()
    service.get_value = AsyncMock(return_value={"en": "Dashboard", "uk": "Панель"})

    result = await service.get_localizable_text(
        "dashboard_title",
        LocalizableValue({"en": "Default"}),
    )

    assert result == LocalizableValue({"en": "Dashboard", "uk": "Панель"})


@pytest.mark.asyncio
async def test_get_localizable_text_uses_default_when_setting_is_empty():
    service = SettingsService()
    default = LocalizableValue({"en": "Dashboard"})
    service.get_value = AsyncMock(return_value=None)

    assert await service.get_localizable_text("dashboard_title", default) == default


@pytest.mark.asyncio
async def test_get_localizable_text_rejects_invalid_culture_codes():
    service = SettingsService()
    service.get_value = AsyncMock(return_value={"xx": "Invalid"})

    with pytest.raises(ValueError, match="Invalid culture code"):
        await service.get_localizable_text(
            "dashboard_title",
            LocalizableValue({"en": "Dashboard"}),
        )
