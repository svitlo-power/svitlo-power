from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Tuple

from beanie import PydanticObjectId

from shared.models.login_history import LoginHistory
from ..interfaces.base import DataQuery


class ILoginHistoryRepository(ABC):

    @abstractmethod
    async def get_login_history(
        self,
        user_id: PydanticObjectId,
    ) -> List[LoginHistory]:
        ...

    @abstractmethod
    async def add_login_history(
        self,
        user_id: PydanticObjectId,
        ip_address: str = None,
    ) -> PydanticObjectId:
        ...
