from abc import ABC, abstractmethod
from beanie import PydanticObjectId

from shared.models.announcement import Announcement


class IAnnouncementsRepository(ABC):

    @abstractmethod
    async def get_all(self) -> list[Announcement]:
        ...

    @abstractmethod
    async def add(self, announcement: Announcement) -> Announcement:
        ...

    @abstractmethod
    async def delete(self, announcement_id: PydanticObjectId) -> bool:
        ...
