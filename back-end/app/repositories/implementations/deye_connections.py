from typing import List

from beanie import PydanticObjectId

from ..interfaces.deye_connections import IDeyeConnectionsRepository
from shared.models.deye_connection import DeyeConnection


class DeyeConnectionsRepository(IDeyeConnectionsRepository):

    async def get_connections(self) -> List[DeyeConnection]:
        return await DeyeConnection.find().sort(DeyeConnection.name).to_list()

    async def get_connection(self, connection_id: PydanticObjectId) -> DeyeConnection | None:
        return await DeyeConnection.find_one(DeyeConnection.id == connection_id)

    async def add_connection(self, connection: DeyeConnection) -> DeyeConnection:
        await connection.insert()
        return connection

    async def save_connection(self, connection: DeyeConnection):
        await connection.save()

    async def delete_connection(self, connection_id: PydanticObjectId):
        connection = await self.get_connection(connection_id)
        if connection is not None:
            await connection.delete()

    async def count(self) -> int:
        return await DeyeConnection.find().count()
