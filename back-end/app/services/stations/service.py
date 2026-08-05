import asyncio
from datetime import datetime
from typing import List
from beanie import PydanticObjectId
from injector import inject

from app.repositories import IStationsRepository, IStationsDataRepository
from shared.models import Station, StationData
from shared.services.events.service import EventsService
from ..base import BaseService
from ..station_connections import StationConnectionsService


@inject
class StationsService(BaseService):
    def __init__(
        self,
        events: EventsService,
        station_connections: StationConnectionsService,
        stations: IStationsRepository,
        stations_data: IStationsDataRepository,
    ):
        super().__init__(events)
        self._station_connections = station_connections
        self._stations = stations
        self._stations_data = stations_data

    async def get_stations(self):
        return await self._stations.get_stations(all=True)

    async def _get_station_data(self, station: Station, last_seconds: int):
        station_data = await self._stations_data.get_full_station_data(station.id, last_seconds)
        return station, station_data

    async def _get_station_data_range(self, station: Station, start_date: datetime, end_date: datetime):
        station_data = await self._stations_data.get_full_station_data_range(station.id, start_date, end_date)
        return station, station_data

    async def get_station_data(self, station_id: str, last_seconds: int) -> tuple[Station, List[StationData]]:
        station = await self._stations.get_station(station_id)
        if not station:
            return None, None

        return await self._get_station_data(station, last_seconds)

    async def get_stations_data(self, last_seconds: int) -> List[tuple[Station, List[StationData]]]:
        stations = await self._stations.get_stations()
        tasks = [
            asyncio.create_task(self._get_station_data(station, last_seconds))
            for station in stations
        ]

        return await asyncio.gather(*tasks)

    async def get_stations_data_range(self, start_date: datetime, end_date: datetime) -> List[tuple[Station, List[StationData]]]:
        stations = await self._stations.get_stations()
        tasks = [
            asyncio.create_task(self._get_station_data_range(station, start_date, end_date))
            for station in stations
        ]

        return await asyncio.gather(*tasks)

    async def edit_station(
        self,
        station_id: str,
        enabled: bool,
        order: int,
        battery_capacity: float,
        station_alias: str,
    ):
        await self._stations.edit_station(
            station_id       = station_id,
            enabled          = enabled,
            order            = order,
            battery_capacity = battery_capacity,
            station_alias    = station_alias
        )

    async def sync_stations(self, connection_ids: List[PydanticObjectId] | None = None):
        for connection in self._station_connections.get_connections():
            if connection_ids is not None and connection.id not in connection_ids:
                continue

            client = await self._station_connections.get_client(connection.id)
            if client is None:
                continue

            stations = await client.get_station_list()
            if stations is None:
                continue
            for station in stations.station_list:
                await self._stations.add_station(station, connection.id)

    async def sync_stations_data(self):
        stations = await self._stations.get_stations()

        for station in stations:
            client = await self._station_connections.get_client(station.connection_id)
            if client is None:
                continue

            station_data = await client.get_station_data(station.station_id)
            if station_data is None:
                continue

            await self._stations_data.add_station_data(station, station_data)
        await self.broadcast_public("station_data_updated")
