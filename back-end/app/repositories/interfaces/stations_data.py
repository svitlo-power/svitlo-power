from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Optional

from beanie import PydanticObjectId

from shared.models import Station, StationData
from app.models import StationStatisticData
from app.models.deye import DeyeStationData
from shared.repositories import IStationsDataReadRepository


class IStationsDataRepository(IStationsDataReadRepository):

    @abstractmethod
    async def add_station_data(self, station: Station, station_data: DeyeStationData):
        ...

    @abstractmethod
    async def get_full_station_data(self, station_id: str, last_seconds: int) -> List[StationData]:
        ...

    @abstractmethod
    async def get_station_data_tuple(station_id: str) -> Optional[StationStatisticData]:
        ...

    @abstractmethod
    async def delete_old_data(self, keep_days: int):
        ...
