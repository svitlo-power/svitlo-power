from abc import abstractmethod

from beanie import PydanticObjectId

from app.models.deye import DeyeStation
from shared.repositories import IStationsReadRepository


class IStationsRepository(IStationsReadRepository):

    @abstractmethod
    async def edit_station(
        self,
        station_id: str,
        enabled: bool,
        order: int,
        battery_capacity: float,
        station_alias: str,
    ):
        ...

    @abstractmethod
    async def add_station(self, station: DeyeStation, connection_id: PydanticObjectId):
        ...

    @abstractmethod
    async def count_by_connection(self, connection_id: PydanticObjectId) -> int:
        ...

    @abstractmethod
    async def assign_connection_to_unassigned(self, connection_id: PydanticObjectId):
        ...
