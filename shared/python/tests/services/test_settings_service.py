from unittest.mock import AsyncMock
from unittest.mock import MagicMock, patch

import pytest
from beanie import PydanticObjectId

from shared.models.localizable_value import LocalizableValue
from shared.models.system_setting import SystemSetting, SystemSettingCategory
from shared.services.settings.service import SettingsService


def test_system_setting_accepts_localizable_text_value():
    setting = SystemSetting(
        key="charge_target_soc",
        label="Dashboard title",
        description="Localized dashboard title",
        setting_type="localizable_text",
        default_value={"en": "Dashboard", "uk": "Панель керування"},
        value={"en": "My dashboard", "uk": "Моя панель"},
        category="dashboard",
    )

    assert isinstance(setting.default_value, LocalizableValue)
    assert isinstance(setting.value, LocalizableValue)
    assert isinstance(setting.label, LocalizableValue)
    assert isinstance(setting.description, LocalizableValue)
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
async def test_get_localizable_text_uses_default_for_empty_localizable_value():
    service = SettingsService()
    default = LocalizableValue({"en": "Dashboard", "uk": "Панель"})
    service.get_value = AsyncMock(return_value={})

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


@pytest.mark.asyncio
async def test_get_settings_grouped_by_category_includes_category_metadata():
    category_id = PydanticObjectId("64a1a1a1a1a1a1a1a1a1a1a1")
    category = MagicMock(
        id=category_id,
        label=LocalizableValue({"en": "Dashboard", "uk": "Панель"}),
    )
    setting = SystemSetting(
        key="charge_target_soc",
        label=LocalizableValue({"en": "Title", "uk": "Назва"}),
        description=LocalizableValue({"en": "Description", "uk": "Опис"}),
        setting_type="text",
        default_value="",
        category_id=category_id,
    )
    service = SettingsService()
    service.get_all_settings = AsyncMock(return_value=[setting])
    category_query = MagicMock()
    category_query.to_list = AsyncMock(return_value=[category])

    with patch.object(SystemSettingCategory, "find_all", return_value=category_query):
        grouped = await service.get_settings_grouped_by_category()

    assert grouped[str(category_id)] == {
        "category": category,
        "settings": [setting],
    }


@pytest.mark.asyncio
async def test_get_settings_grouped_by_category_includes_dashboard_configuration_settings():
    category_id = PydanticObjectId("64b2b2b2b2b2b2b2b2b2b2b2")
    category = MagicMock(
        id=category_id,
        label=LocalizableValue({"en": "Dashboard", "uk": "Панель"}),
    )
    setting = SystemSetting(
        key="dashboard_title",
        label="Dashboard title",
        description="Dashboard title",
        setting_type="localizable_text",
        default_value={},
        category_id=category_id,
    )
    service = SettingsService()
    service.get_all_settings = AsyncMock(return_value=[setting])
    category_query = MagicMock()
    category_query.to_list = AsyncMock(return_value=[category])

    with patch.object(SystemSettingCategory, "find_all", return_value=category_query):
        grouped = await service.get_settings_grouped_by_category()

    assert grouped[str(category_id)]["settings"] == [setting]


@pytest.mark.asyncio
async def test_get_settings_grouped_by_category_rejects_missing_category_reference():
    setting = SystemSetting(
        key="charge_target_soc",
        label="Title",
        description="Description",
        setting_type="text",
        default_value="",
    )
    service = SettingsService()
    service.get_all_settings = AsyncMock(return_value=[setting])

    with pytest.raises(RuntimeError, match="has no category reference"):
        await service.get_settings_grouped_by_category()


@pytest.mark.asyncio
async def test_reset_to_defaults_skips_non_editable_settings():
    editable = SystemSetting(
        key="charge_target_soc",
        label="Charge target SOC",
        description="Charge target SOC",
        setting_type="number",
        default_value=80,
        value=70,
        editable=True,
    )
    read_only = SystemSetting(
        key="dashboard_outages_schedule_region",
        label="Schedule region",
        description="Schedule region ID",
        setting_type="number",
        default_value=0,
        value=25,
        editable=False,
    )
    service = SettingsService()
    service.get_all_settings = AsyncMock(return_value=[editable, read_only])

    with patch.object(SystemSetting, "save", new_callable=AsyncMock) as save:
        assert await service.reset_to_defaults() == 1

    assert editable.value is None
    assert read_only.value == 25
    assert save.await_count == 1
