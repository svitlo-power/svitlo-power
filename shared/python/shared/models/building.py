from beanie import Document, Link
from typing import List, Optional

from .localizable_value import LocalizableValue
from .beanie_filter import BeanieFilter
from .lookup import LookupModel, LookupValue
from .station import Station
from .user import User


class Building(Document, LookupModel):
    name: LocalizableValue
    color: str
    enabled: bool

    station: Optional[Link[Station]] = None
    report_users: List[Link[User]] = []

    order: int = 1

    class Settings:
        name = "buildings"

    def to_dict(self):
        return {
            "id": str(self.id),
            "name": self.name,
            "color": self.color,
            "station_id": str(self.station.id) if self.station else None,
            "report_user_ids": [str(user.id) for user in self.report_users] if self.report_users else [],
            "order": self.order,
        }

    @classmethod
    async def get_lookup_values(self, filter: BeanieFilter) -> List[LookupValue]:
        buildings = await self.find_all(filter).sort(Building.order).to_list()
        return [LookupValue(
            value = b.id,
            text  = b.name
        ) for b in buildings]
