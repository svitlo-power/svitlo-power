from abc import ABC, abstractmethod
from typing import List

from beanie import PydanticObjectId

from shared.models.station_connection import StationConnection


class IStationConnectionsRepository(ABC):

    @abstractmethod
    async def get_connections(self) -> List[StationConnection]:
        ...

    @abstractmethod
    async def get_connection(self, connection_id: PydanticObjectId) -> StationConnection | None:
        ...

    @abstractmethod
    async def add_connection(self, connection: StationConnection) -> StationConnection:
        ...

    @abstractmethod
    async def save_connection(self, connection: StationConnection):
        ...

    @abstractmethod
    async def delete_connection(self, connection_id: PydanticObjectId):
        ...

    @abstractmethod
    async def count(self) -> int:
        ...
