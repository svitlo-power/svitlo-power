from abc import ABC, abstractmethod
from typing import List, Optional

from beanie import PydanticObjectId

from shared.models.building import Building
from shared.models.dashboard_config import DashboardConfig


class IDashboardRepository(ABC):

    @abstractmethod
    async def get_building(self, id: PydanticObjectId) -> Building:
        ...

    @abstractmethod
    async def edit_building(self, building: Building):
        ...

    @abstractmethod
    async def create_building(self, building: Building) -> PydanticObjectId:
        ...

    @abstractmethod
    async def delete_building(self, building: Building):
        ...
    
    @abstractmethod
    async def get_buildings(
        self,
        ids: Optional[List[PydanticObjectId]] = None,
        all: bool = False
    ) -> List[Building]:
        ...

    @abstractmethod
    async def get_config(self) -> DashboardConfig:
        ...

    @abstractmethod
    async def save_config(self, config: DashboardConfig):
        ...