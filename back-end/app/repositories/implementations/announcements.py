from beanie import PydanticObjectId

from shared.models.announcement import Announcement
from ..interfaces.announcements import IAnnouncementsRepository


class AnnouncementsRepository(IAnnouncementsRepository):

    async def get_all(self) -> list[Announcement]:
        return await Announcement.find_all().sort(-Announcement.created_at).to_list()

    async def add(self, announcement: Announcement) -> Announcement:
        await announcement.insert()
        return announcement

    async def delete(self, announcement_id: PydanticObjectId) -> bool:
        result = await Announcement.find(Announcement.id == announcement_id).delete()
        return bool(result and result.deleted_count)
