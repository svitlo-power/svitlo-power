from typing import List

from beanie import PydanticObjectId

from ..interfaces.station_connections import IStationConnectionsRepository
from shared.models.station_connection import StationConnection


class StationConnectionsRepository(IStationConnectionsRepository):

    async def get_connections(self) -> List[StationConnection]:
        return await StationConnection.find().sort(StationConnection.name).to_list()

    async def get_connection(self, connection_id: PydanticObjectId) -> StationConnection | None:
        return await StationConnection.find_one(StationConnection.id == connection_id)

    async def add_connection(self, connection: StationConnection) -> StationConnection:
        await connection.insert()
        return connection

    async def save_connection(self, connection: StationConnection):
        await connection.save()

    async def delete_connection(self, connection_id: PydanticObjectId):
        connection = await self.get_connection(connection_id)
        if connection is not None:
            await connection.delete()

    async def count(self) -> int:
        return await StationConnection.find().count()
