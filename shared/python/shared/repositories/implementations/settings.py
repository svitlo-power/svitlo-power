from typing import List

from shared.models.system_setting import SystemSetting
from shared.repositories.interfaces.settings import ISettingsRepository


class SettingsRepository(ISettingsRepository):

    async def get_settings_by_keys(self, keys: List[str]) -> List[SystemSetting]:
        return await SystemSetting.find(
            {"key": {"$in": keys}}
        ).to_list()

    async def get_all_settings(self) -> List[SystemSetting]:
        return await SystemSetting.find_all().to_list()
