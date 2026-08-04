from abc import ABC, abstractmethod
from typing import List

from beanie import PydanticObjectId

from shared.models.deye_connection import DeyeConnection


class IDeyeConnectionsRepository(ABC):

    @abstractmethod
    async def get_connections(self) -> List[DeyeConnection]:
        ...

    @abstractmethod
    async def get_connection(self, connection_id: PydanticObjectId) -> DeyeConnection | None:
        ...

    @abstractmethod
    async def add_connection(self, connection: DeyeConnection) -> DeyeConnection:
        ...

    @abstractmethod
    async def save_connection(self, connection: DeyeConnection):
        ...

    @abstractmethod
    async def delete_connection(self, connection_id: PydanticObjectId):
        ...

    @abstractmethod
    async def count(self) -> int:
        ...
