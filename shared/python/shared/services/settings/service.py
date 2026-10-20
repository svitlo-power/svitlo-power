from typing import List, Optional, Union
from datetime import datetime
from injector import inject, singleton
from beanie import PydanticObjectId

from shared.models.system_setting import SystemSetting, SystemSettingValue


@singleton
class SettingsService:
    @inject
    def __init__(self):
        pass

    async def get_setting(self, key: str) -> Optional[SystemSetting]:
        """Get a setting by key."""
        return await SystemSetting.find_one(SystemSetting.key == key)

    async def get_value(self, key: str, default: SystemSettingValue = None) -> SystemSettingValue:
        """Get the current value of a setting (or default if not set)."""
        setting = await self.get_setting(key)
        if setting and setting.value is not None:
            return setting.value
        if setting:
            return setting.default_value
        return default

    async def get_number(self, key: str, default: float = 0) -> float:
        """Get a setting value as a number."""
        value = await self.get_value(key, default)
        try:
            return float(value)
        except (ValueError, TypeError):
            return default

    async def get_int(self, key: str, default: int = 0) -> int:
        """Get a setting value as an integer."""
        value = await self.get_value(key, default)
        try:
            return int(value)
        except (ValueError, TypeError):
            return default

    async def get_text(self, key: str, default: str = "") -> str:
        """Get a setting value as text."""
        value = await self.get_value(key, default)
        return str(value) if value is not None else default

    async def get_boolean(self, key: str, default: bool = False) -> bool:
        """Get a setting value as boolean."""
        value = await self.get_value(key, default)
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ("true", "1", "yes", "on")
        return bool(value)

    async def get_datetime(self, key: str, default: SystemSettingValue = None) -> SystemSettingValue:
        """Get a setting value as datetime."""
        value = await self.get_value(key, default)
        if isinstance(value, datetime):
            return value
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value)
            except ValueError:
                return default
        return default

    async def get_timestamp(self, key: str, default: SystemSettingValue = None) -> SystemSettingValue:
        """Get a setting value as timestamp."""
        return await self.get_datetime(key, default)

    async def get_select(self, key: str, default: SystemSettingValue = None) -> SystemSettingValue:
        """Get a setting value for select type."""
        return await self.get_value(key, default)

    async def set_value(self, key: str, value: SystemSettingValue) -> Optional[SystemSetting]:
        """Set a setting value."""
        setting = await self.get_setting(key)
        if setting:
            setting.value = value
            setting.updated_at = datetime.utcnow()
            await setting.save()
            return setting
        return None

    async def create_or_update(self, setting: SystemSetting) -> SystemSetting:
        """Create or update a setting."""
        existing = await self.get_setting(setting.key)
        if existing:
            existing.label = setting.label
            existing.description = setting.description
            existing.setting_type = setting.setting_type
            existing.default_value = setting.default_value
            existing.value = setting.value
            existing.validation = setting.validation
            existing.category = setting.category
            existing.updated_at = datetime.utcnow()
            await existing.save()
            return existing
        else:
            await setting.insert()
            return setting

    async def get_all_settings(self) -> List[SystemSetting]:
        """Get all settings."""
        return await SystemSetting.find_all().to_list()

    async def get_settings_by_category(self, category: str) -> List[SystemSetting]:
        """Get settings by category."""
        return await SystemSetting.find(SystemSetting.category == category).to_list()

    async def get_settings_grouped_by_category(self) -> dict:
        """Get all settings grouped by category."""
        settings = await self.get_all_settings()
        grouped = {}
        for setting in settings:
            if setting.category not in grouped:
                grouped[setting.category] = []
            grouped[setting.category].append(setting)
        return grouped

    async def bulk_update(self, updates: dict[str, SystemSettingValue]) -> dict[str, bool]:
        """Bulk update settings."""
        results: dict[str, bool] = {}
        for key, value in updates.items():
            setting = await self.set_value(key, value)
            results[key] = setting is not None
        return results

    async def reset_to_defaults(self) -> int:
            """Reset all settings to their default values."""
            settings = await self.get_all_settings()
            count = 0
            for setting in settings:
                setting.value = None
                setting.updated_at = datetime.utcnow()
                await setting.save()
                count += 1
            return count