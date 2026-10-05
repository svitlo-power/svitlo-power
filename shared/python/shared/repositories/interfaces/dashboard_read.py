from abc import ABC, abstractmethod
from typing import List, Optional
from beanie import PydanticObjectId
from shared.models.building import Building
from shared.models.dashboard_config import DashboardConfig

class IDashboardReadRepository(ABC):

    @abstractmethod
    async def get_building(self, id: PydanticObjectId) -> Building:
        ...

    @abstractmethod
    async def get_building_by_station_id(self, station_id: int) -> Optional[Building]:
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
