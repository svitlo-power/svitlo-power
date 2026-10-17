from abc import ABC, abstractmethod
from typing import List
from beanie import PydanticObjectId

from shared.models.station import Station
from shared.repositories.interfaces.stations_read import IStationsReadRepository


class StationsReadRepository(IStationsReadRepository):

    async def get_stations(self, all: bool = False) -> List[Station]:
        query = {} if all else {"enabled": True}
        return await Station.find(query).sort(Station.order).to_list()

    async def get_station(self, station_id: str) -> Station | None:
        return await Station.find_one(Station.id == PydanticObjectId(station_id))

    async def get_station_by_station_id(self, station_id: int) -> Station | None:
        return await Station.find_one(Station.station_id == station_id)
