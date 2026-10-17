from abc import ABC, abstractmethod
from typing import List, Optional
from beanie import PydanticObjectId
from shared.models.building import Building
from shared.models.dashboard_config import DashboardConfig
from shared.repositories.interfaces import IDashboardReadRepository

class DashboardReadRepository(IDashboardReadRepository):

    async def get_building(self, id: PydanticObjectId) -> Building:
        return await Building.get(id, fetch_links=True)

    async def get_building_by_station_id(
        self,
        station_id: int,
    ) -> Optional[Building]:
        return await Building.find_one(
            Building.station.id == station_id,
            fetch_links=True,
        )
    
    async def get_buildings(
        self,
        ids: Optional[List[PydanticObjectId]] = None,
        all: bool = False,
    ) -> List[Building]:
        query = {}

        if ids is not None:
            query["_id"] = {"$in": ids}
        elif not all:
            query["enabled"] = True

        return (
            await Building.find(query, fetch_links=True)
            .sort(Building.order)
            .to_list()
        )

    async def get_config(self) -> DashboardConfig:
        return await DashboardConfig.find_one()
