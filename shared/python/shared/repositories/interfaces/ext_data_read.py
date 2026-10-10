from abc import ABC, abstractmethod
from datetime import datetime
from typing import List
from beanie import PydanticObjectId

from shared.models.ext_data import ExtData

class IExtDataReadRepository(ABC):

    @abstractmethod
    async def get_last_ext_data_by_user_id(self, user_id: PydanticObjectId) -> ExtData:
        ...

    @abstractmethod
    async def get_ext_data_statistics(
        self,
        user_id: PydanticObjectId,
        start_date: datetime,
        end_date: datetime,
    ):
        ...

    @abstractmethod
    async def get_last_ext_data_before_date(self, user_id: int, before_date: datetime):
        ...
