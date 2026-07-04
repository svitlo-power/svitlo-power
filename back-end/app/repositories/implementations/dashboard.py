from typing import List, Optional
from beanie import PydanticObjectId

from shared.models.building import Building
from shared.models.dashboard_config import DashboardConfig
from ..interfaces.dashboard import IDashboardRepository

class DashboardRepository(IDashboardRepository):

    async def get_building(self, id: PydanticObjectId) -> Building:
        return await Building.get(id, fetch_links=True)
    
    async def edit_building(self, building: Building):
        await building.save()

    async def create_building(self, building: Building) -> PydanticObjectId:
        await building.insert()
        return building.id

    async def delete_building(self, building: Building):
        await building.delete()

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

    async def save_config(self, config: DashboardConfig):
        existing_config = await DashboardConfig.find_one()
        if existing_config:
            existing_config.title = config.title
            existing_config.enable_outages_schedule = config.enable_outages_schedule
            existing_config.outages_schedule_queue = config.outages_schedule_queue
            await existing_config.save()
        else:
            await config.insert()
