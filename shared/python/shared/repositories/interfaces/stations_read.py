from abc import ABC, abstractmethod
from typing import List

from shared.models.station import Station


class IStationsReadRepository(ABC):

    @abstractmethod
    async def get_station(self, station_id: str) -> Station | None:
        ...

    @abstractmethod
    async def get_station_by_station_id(self, station_id: int) -> Station | None:
        ...

    @abstractmethod
    async def get_stations(self, all: bool = False) -> List[Station]:
        ...
