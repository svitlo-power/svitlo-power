from typing import List, Optional
from datetime import datetime
from beanie import PydanticObjectId
from injector import inject, singleton

from shared.models.localizable_value import LocalizableValue
from shared.models.system_setting import SystemSetting, SystemSettingCategory, SystemSettingValue
from shared.repositories import ISettingsRepository


@singleton
class SettingsService:
    @inject
    def __init__(
        self,
        settings_repo: ISettingsRepository,
    ):
        self._settings_repo = settings_repo

    async def get_setting(self, key: str) -> Optional[SystemSetting]:
        """Get a setting by key."""
        settings = await self._settings_repo.get_settings_by_keys([key])
        return settings[0] if settings else None

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

    async def get_localizable_text(
        self,
        key: str,
        default: LocalizableValue,
    ) -> LocalizableValue:
        """Get a setting value as localized text."""
        value = await self.get_value(key, default)
        if value is None:
            return default
        if isinstance(value, LocalizableValue):
            return value if value.root else default
        if isinstance(value, dict):
            localized_value = LocalizableValue.model_validate(value)
            return localized_value if localized_value.root else default
        raise TypeError(f"Setting '{key}' does not contain localized text")

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
            existing.editable = setting.editable
            existing.category_id = setting.category_id
            existing.updated_at = datetime.utcnow()
            await existing.save()
            return existing
        else:
            await setting.insert()
            return setting

    async def get_all_settings(self) -> List[SystemSetting]:
        """Get all settings."""
        return await self._settings_repo.get_all_settings()

    async def get_settings_by_category(
        self,
        category_id: PydanticObjectId,
    ) -> List[SystemSetting]:
        """Get settings by category."""
        all_settings = await self._settings_repo.get_all_settings()
        return [s for s in all_settings if s.category_id == category_id]

    async def get_settings_grouped_by_category(
        self,
        keys: Optional[List[str]] = None,
    ) -> dict:
        """Get settings grouped by category.

        If keys is provided, only settings with matching keys are returned from the database.
        """
        if keys:
            settings = await self._settings_repo.get_settings_by_keys(keys)
        else:
            settings = await self._settings_repo.get_all_settings()
        for setting in settings:
            if setting.category_id is None:
                raise RuntimeError(
                    f"Setting '{setting.key}' has no category reference"
                )
        categories = await SystemSettingCategory.find_all().to_list()
        categories_by_id = {str(category.id): category for category in categories}
        grouped = {}
        for setting in settings:
            category_id = str(setting.category_id)
            category = categories_by_id.get(category_id)
            if category is None:
                raise RuntimeError(
                    f"Setting '{setting.key}' references missing category "
                    f"'{category_id}'"
                )
            if category_id not in grouped:
                grouped[category_id] = {"category": category, "settings": []}
            grouped[category_id]["settings"].append(setting)
        return grouped

    async def bulk_update(self, updates: dict[str, SystemSettingValue]) -> dict[str, bool]:
        """Bulk update settings."""
        results: dict[str, bool] = {}
        for key, value in updates.items():
            setting = await self.set_value(key, value)
            results[key] = setting is not None
        return results
