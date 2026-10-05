import asyncio
from typing import List, Optional
from beanie import PydanticObjectId

from shared.models.building import Building
from shared.models.dashboard_config import DashboardConfig
from shared.repositories import DashboardReadRepository
from ..interfaces.dashboard import IDashboardRepository

class DashboardRepository(DashboardReadRepository, IDashboardRepository):

    async def edit_building(self, building: Building):
        await building.save()

    async def create_building(self, building: Building) -> PydanticObjectId:
        await building.insert()
        return building.id

    async def delete_building(self, building: Building):
        await building.delete()

    async def reorder_buildings(self, buildings: List[Building]):
        for index, building in enumerate(buildings, start=1):
            building.order = index
        await asyncio.gather(*(building.save() for building in buildings))

    async def save_config(self, config: DashboardConfig):
        existing_config = await DashboardConfig.find_one()
        if existing_config:
            existing_config.title = config.title
            existing_config.enable_outages_schedule = config.enable_outages_schedule
            existing_config.outages_schedule_queue = config.outages_schedule_queue
            await existing_config.save()
        else:
            await config.insert()
