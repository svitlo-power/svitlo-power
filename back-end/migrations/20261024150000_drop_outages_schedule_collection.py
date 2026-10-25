from beanie import free_fall_migration

from shared.models.outages_schedule import OutagesSchedule


class Forward:
    @free_fall_migration(document_models=[OutagesSchedule])
    async def drop_outages_schedule_collection(self, session):
        await OutagesSchedule.get_pymongo_collection().drop(session=session)


class Backward:
    @free_fall_migration(document_models=[OutagesSchedule])
    async def recreate_outages_schedule_collection(self, session):
        await OutagesSchedule.get_pymongo_collection().create_index(
            "queue",
            session=session,
        )
