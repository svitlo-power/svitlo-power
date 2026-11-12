from beanie import free_fall_migration

from shared.models.station import Station


class Forward:
    @free_fall_migration(document_models=[Station])
    async def add_station_soc_overrides(self, session):
        stations_collection = Station.get_pymongo_collection()
        await stations_collection.update_many(
            {},
            {
                "$set": {
                    "discharge_target_soc": None,
                    "charge_target_soc": None,
                }
            },
            session=session,
        )


class Backward:
    @free_fall_migration(document_models=[Station])
    async def remove_station_soc_overrides(self, session):
        stations_collection = Station.get_pymongo_collection()
        await stations_collection.update_many(
            {},
            {
                "$unset": {
                    "discharge_target_soc": "",
                    "charge_target_soc": "",
                }
            },
            session=session,
        )
