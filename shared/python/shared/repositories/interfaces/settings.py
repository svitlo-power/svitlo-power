from abc import ABC, abstractmethod
from typing import List, Optional

from shared.models.system_setting import SystemSetting


class ISettingsRepository(ABC):

    @abstractmethod
    async def get_settings_by_keys(self, keys: List[str]) -> List[SystemSetting]:
        ...

    @abstractmethod
    async def get_all_settings(self) -> List[SystemSetting]:
        ...
