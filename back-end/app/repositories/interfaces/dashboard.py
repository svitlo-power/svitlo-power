from abc import ABC, abstractmethod
from typing import List, Optional

from beanie import PydanticObjectId

from shared.models.building import Building
from shared.models.dashboard_config import DashboardConfig
from shared.repositories import IDashboardReadRepository


class IDashboardRepository(IDashboardReadRepository, ABC):

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
    async def reorder_buildings(self, buildings: List[Building]):
        ...

    @abstractmethod
    async def save_config(self, config: DashboardConfig):
        ...