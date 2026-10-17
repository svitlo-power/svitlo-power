from abc import abstractmethod
from datetime import datetime
from typing import List
from beanie import PydanticObjectId

from shared.models.ext_data import ExtData
from shared.repositories import IExtDataReadRepository
from .base import DataQuery

class IExtDataRepository(IExtDataReadRepository):
    
    @abstractmethod
    async def get_ext_data(self, query: DataQuery = None) -> tuple[List[ExtData], int]:
        ...

    @abstractmethod
    async def get_ext_data_by_id(self, ext_data_id: PydanticObjectId) -> ExtData:
        ...

    @abstractmethod
    async def add_ext_data(
        self,
        user_id: PydanticObjectId,
        grid_state: bool,
        date: datetime,
    ) -> PydanticObjectId:
        ...

    @abstractmethod
    async def delete(self, ext_data_id: PydanticObjectId) -> bool:
        ...

    @abstractmethod
    async def delete_old_data(self, keep_days: int):
        ...
