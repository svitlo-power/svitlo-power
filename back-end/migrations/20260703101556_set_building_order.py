from beanie import free_fall_migration

from shared.models.building import Building


class Forward:
    @free_fall_migration(document_models=[Building])
    async def set_order(self, session):
        buildings = await Building.find_all().sort("_id").to_list()

        for order, building in enumerate(buildings, start=1):
            building.order = order
            await building.save(session=session)

class Backward:
    @free_fall_migration(document_models=[Building])
    async def unset_order(self, session):
        buildings = await Building.find_all().to_list()

        for building in buildings:
            building.order = 1
            await building.save(session=session)
