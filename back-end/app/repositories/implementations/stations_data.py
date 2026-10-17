import logging
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from beanie import PydanticObjectId
from injector import inject

from app.settings import Settings
from app.models import StationStatisticData
from ..interfaces.stations_data import IStationsDataRepository
from shared.repositories import StationsDataReadRepository
from shared.models import Station, StationData
from app.models.deye import DeyeStationData


logger = logging.getLogger(__name__)


@inject
class StationsDataRepository(StationsDataReadRepository, IStationsDataRepository):

    async def add_station_data(self, station: Station, station_data: DeyeStationData):
        try:
            last_update_time = datetime.fromtimestamp(station_data.last_update_time, timezone.utc)
            existing_record = await StationData.find_one(
                StationData.station_id == station.id,
                StationData.last_update_time == last_update_time,
            )

            if not existing_record:
                new_record = StationData(
                    station_id          = station.id,
                    battery_power       = station_data.battery_power,
                    battery_soc         = station_data.battery_soc,
                    charge_power        = station_data.charge_power,
                    code                = station_data.code,
                    consumption_power   = station_data.consumption_power,
                    discharge_power     = station_data.discharge_power,
                    generation_power    = station_data.generation_power,
                    grid_power          = station_data.grid_power,
                    irradiate_intensity = station_data.irradiate_intensity,
                    last_update_time    = last_update_time,
                    msg                 = station_data.msg,
                    purchase_power      = station_data.purchase_power,
                    request_id          = station_data.request_id,
                    wire_power          = station_data.wire_power
                )
                await new_record.insert()
        except Exception as e:
            logger.error(f"Error updating station data:", exc_info=True)

    async def get_full_station_data(self, station_id: PydanticObjectId, last_seconds: int) -> List[StationData]:
        try:
            min_date = datetime.now(timezone.utc) - timedelta(seconds=last_seconds)
            stations = await (
                StationData.find(
                    StationData.station_id == station_id,
                    StationData.last_update_time >= min_date
                )
                .sort(StationData.last_update_time)
                .to_list()
            )
            return stations
        except Exception as e:
            logger.error(f"Error fetching station data: {e}")
            return []

    async def get_last_station_data(
        self,
        station_id: PydanticObjectId,
    ) -> StationData:
        station = await (
            StationData.find(
                StationData.station_id == station_id,
            )
            .sort(-StationData.last_update_time)
            .first_or_none()
        )
        return station

    async def get_station_data_tuple(
        self,
        station_id: str,
    ) -> Optional[StationStatisticData]:
        try:
            station = await Station.find_one(Station.station_id == station_id)
            if not station:
                return None

            stations = (
                await StationData.find(
                    StationData.station_id == station.id
                )
                .sort("-last_update_time")
                .limit(2)
                .to_list()
            )

            if not stations:
                return None

            previous = stations[1] if len(stations) == 2 else None
            current = stations[0]

            return StationStatisticData(previous, current)

        except Exception as e:
            logger.error(f"Error fetching station data tuple: {e}")
            return None

    async def delete_old_data(self, keep_days: int):
        timeout = datetime.now(timezone.utc) - timedelta(days = keep_days)
        logger.info(f"removing stations data older than {timeout}")

        await StationData.find(
            StationData.last_update_time < timeout
        ).delete()
