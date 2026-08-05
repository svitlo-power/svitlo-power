import logging
from datetime import datetime, timezone
import traceback
from typing import List

from beanie import PydanticObjectId

from ..interfaces.stations import IStationsRepository
from shared.models.station import Station
from app.models.deye import DeyeStation


logger = logging.getLogger(__name__)


class StationsRepository(IStationsRepository):

    async def get_stations(self, all: bool = False) -> List[Station]:
        query = {} if all else {"enabled": True}
        return await Station.find(query).sort(Station.order).to_list()

    async def get_station(self, station_id: str) -> Station | None:
        return await Station.find_one(Station.id == PydanticObjectId(station_id))

    async def get_station_by_station_id(self, station_id: int) -> Station | None:
        return await Station.find_one(Station.station_id == station_id)

    async def edit_station(
        self,
        station_id: str,
        enabled: bool,
        order: int,
        battery_capacity: float,
        station_alias: str,
    ):
        station = await self.get_station(station_id)
        if station is None:
            raise ValueError(f"Cannot find station by id {station_id}")

        station.enabled = enabled
        station.order = order
        station.battery_capacity = battery_capacity
        station.station_alias = station_alias
        await station.save()

    async def count_by_connection(self, connection_id: PydanticObjectId) -> int:
        return await Station.find(Station.connection_id == connection_id).count()

    async def assign_connection_to_unassigned(self, connection_id: PydanticObjectId):
        await Station.find({"connection_id": None}).update_many(
            {"$set": {"connection_id": connection_id}}
        )

    async def add_station(self, station: DeyeStation, connection_id: PydanticObjectId):
        try:
            max_station = await Station.find().sort(-Station.order).first_or_none()
            max_order = max_station.order if max_station else 0

            existing_station = await Station.find_one(Station.station_id == station.id)

            if existing_station is None:
                new_record = Station(
                    station_id                = station.id,
                    station_name              = station.name,
                    connection_status         = station.connection_status,
                    contact_phone             = station.contact_phone,
                    created_date              = datetime.fromtimestamp(
                        station.created_date, timezone.utc
                    ),
                    grid_interconnection_type = station.grid_interconnection_type,
                    installed_capacity        = station.installed_capacity,
                    location_address          = station.location_address,
                    location_lat              = station.location_lat,
                    location_lng              = station.location_lng,
                    owner_name                = station.owner_name,
                    region_nation_id          = station.region_nation_id,
                    region_timezone           = station.region_timezone,
                    generation_power          = station.generation_power,
                    last_update_time          = datetime.fromtimestamp(
                        station.last_update_time, timezone.utc
                    ),
                    start_operating_time      = datetime.fromtimestamp(
                        station.start_operating_time, timezone.utc
                    ),
                    order                     = max_order + 1,
                    connection_id             = connection_id,
                )

                await new_record.insert()
            else:
                existing_station.connection_status = station.connection_status
                existing_station.grid_interconnection_type = station.grid_interconnection_type
                existing_station.last_update_time = datetime.fromtimestamp(
                    station.last_update_time, timezone.utc
                )
                existing_station.connection_id = connection_id
                await existing_station.save()

        except Exception as e:
            logger.error(f"Error inserting station:", exc_info=True)
