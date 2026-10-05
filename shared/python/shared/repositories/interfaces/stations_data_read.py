from abc import ABC, abstractmethod
from datetime import datetime
from typing import List

from beanie import PydanticObjectId

from shared.models import AssumedStationStatus, StationData


class IStationsDataReadRepository(ABC):

    @abstractmethod
    async def get_full_station_data_range(
        self,
        station_id: str,
        start_date: datetime,
        end_date: datetime,
    ) -> List[StationData]:
        ...

    @abstractmethod
    async def get_assumed_connection_status(self, station_id: int) -> AssumedStationStatus:
        ...

    @abstractmethod
    async def get_last_station_data(self, station_id: PydanticObjectId) -> StationData:
        ...

    @abstractmethod
    async def get_station_data_average_column(
        self,
        start_date: datetime | None,
        end_date: datetime | None,
        station_id: int,
        column_name: str,
    ) -> float:
        ...
