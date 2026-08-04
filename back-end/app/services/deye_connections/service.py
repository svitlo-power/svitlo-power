import logging
from typing import List

from aiohttp import ClientSession
from beanie import PydanticObjectId
from injector import inject

from app.repositories import IDeyeConnectionsRepository, IStationsRepository
from app.settings import Settings
from app.utils.crypto import SecretCipher, InvalidToken
from shared.models import DeyeConnection
from ..deye_api import DeyeApiService, DeyeConfig


logger = logging.getLogger(__name__)


@inject
class DeyeConnectionsService:
    """Singleton store of Deye connections and their API clients."""

    def __init__(
        self,
        settings: Settings,
        connections: IDeyeConnectionsRepository,
        stations: IStationsRepository,
        session: ClientSession,
    ):
        self._settings = settings
        self._connections_repo = connections
        self._stations_repo = stations
        self._session = session
        self._cipher = SecretCipher(settings.SECRET_KEY)
        self._connections: dict[PydanticObjectId, DeyeConnection] = {}
        self._clients: dict[PydanticObjectId, DeyeApiService] = {}

    async def init(self):
        await self._migrate()
        connections = await self._connections_repo.get_connections()
        self._connections = {c.id: c for c in connections}

    async def shutdown(self):
        for client in self._clients.values():
            await client.shutdown()
        self._clients.clear()

    async def _migrate(self):
        """Create a "Default" connection from the legacy env config and attach
        existing stations to it (or to the first known connection)."""
        settings = self._settings
        if await self._connections_repo.count() == 0:
            required = (
                settings.DEYE_BASE_URL, settings.DEYE_APP_ID, settings.DEYE_APP_SECRET,
                settings.DEYE_EMAIL, settings.DEYE_PASSWORD,
            )
            if not all(required):
                return
            connection = DeyeConnection(
                name                  = "Default",
                base_url              = settings.DEYE_BASE_URL,
                app_id                = settings.DEYE_APP_ID,
                app_secret            = self._cipher.encrypt(settings.DEYE_APP_SECRET),
                email                 = settings.DEYE_EMAIL,
                password              = self._cipher.encrypt(settings.DEYE_PASSWORD),
                sync_stations_on_poll = settings.DEYE_SYNC_STATIONS_ON_POLL,
            )
            await self._connections_repo.add_connection(connection)
            logger.info("Created 'Default' Deye connection from env config")

        connections = await self._connections_repo.get_connections()
        if connections:
            await self._stations_repo.assign_connection_to_unassigned(connections[0].id)

    def get_connections(self) -> List[DeyeConnection]:
        return sorted(self._connections.values(), key=lambda c: c.name.lower())

    def get_connection(self, connection_id: PydanticObjectId) -> DeyeConnection | None:
        return self._connections.get(connection_id)

    async def get_client(self, connection_id: PydanticObjectId) -> DeyeApiService | None:
        connection = self._connections.get(connection_id)
        if connection is None:
            return None

        client = self._clients.get(connection_id)
        if client is None:
            try:
                config = DeyeConfig(
                    base_url              = connection.base_url,
                    app_id                = connection.app_id,
                    app_secret            = self._cipher.decrypt(connection.app_secret),
                    email                 = connection.email,
                    password              = self._cipher.decrypt(connection.password),
                    sync_stations_on_poll = connection.sync_stations_on_poll,
                )
            except InvalidToken:
                logger.error(
                    f"Cannot decrypt credentials of Deye connection '{connection.name}' "
                    f"({connection.id}): SECRET_KEY mismatch"
                )
                return None
            client = DeyeApiService(config, self._session)
            await client.init()
            self._clients[connection_id] = client
        return client

    async def create_connection(
        self,
        name: str,
        base_url: str,
        app_id: str,
        app_secret: str,
        email: str,
        password: str,
        sync_stations_on_poll: bool,
    ) -> DeyeConnection:
        connection = DeyeConnection(
            name                  = name,
            base_url              = base_url,
            app_id                = app_id,
            app_secret            = self._cipher.encrypt(app_secret),
            email                 = email,
            password              = self._cipher.encrypt(password),
            sync_stations_on_poll = sync_stations_on_poll,
        )
        await self._connections_repo.add_connection(connection)
        self._connections[connection.id] = connection
        return connection

    async def update_connection(
        self,
        connection_id: PydanticObjectId,
        name: str,
        base_url: str,
        app_id: str,
        email: str,
        sync_stations_on_poll: bool,
        app_secret: str | None = None,
        password: str | None = None,
    ) -> DeyeConnection:
        connection = await self._connections_repo.get_connection(connection_id)
        if connection is None:
            raise ValueError(f"Cannot find Deye connection by id {connection_id}")

        connection.name = name
        connection.base_url = base_url
        connection.app_id = app_id
        connection.email = email
        connection.sync_stations_on_poll = sync_stations_on_poll
        if app_secret:
            connection.app_secret = self._cipher.encrypt(app_secret)
        if password:
            connection.password = self._cipher.encrypt(password)

        await self._connections_repo.save_connection(connection)
        self._connections[connection.id] = connection
        await self._drop_client(connection.id)
        return connection

    async def delete_connection(self, connection_id: PydanticObjectId):
        await self._drop_client(connection_id)
        self._connections.pop(connection_id, None)
        await self._connections_repo.delete_connection(connection_id)

    async def _drop_client(self, connection_id: PydanticObjectId):
        client = self._clients.pop(connection_id, None)
        if client is not None:
            await client.shutdown()
