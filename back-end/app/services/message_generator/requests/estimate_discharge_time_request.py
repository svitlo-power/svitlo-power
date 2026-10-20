from dataclasses import dataclass
from typing import ClassVar
from injector import Injector

from ..models import TemplateRequest
from app.repositories import IStationsRepository, IStationsDataRepository
from shared.utils import get_estimate_discharge_time


@dataclass(frozen=True)
class EstimateDischargeTimeRequest(TemplateRequest):
    name: ClassVar[str] = "get_estimate_discharge_time"

    station_id: int

    async def resolve(self, injector: Injector) -> str:
        stations_repo = injector.get(IStationsRepository)
        stations_data_repo = injector.get(IStationsDataRepository)

        station = await stations_repo.get_station_by_station_id(self.station_id)
        if station is None or station.battery_capacity is None:
            return "00:00"

        station_data = await stations_data_repo.get_last_station_data(station.id)
        if station_data is None:
            return "00:00"

        batt_soc = station_data.battery_soc
        if batt_soc is None:
            return "00:00"

        # Get average consumption from the last 25 minutes (default period)
        from datetime import datetime, timedelta, timezone
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(minutes=25)

        average_consumption_w = await stations_data_repo.get_station_data_average_column(
            start_date=start_date,
            end_date=end_date,
            station_id=self.station_id,
            column_name="consumption_power",
        ) or 0

        average_consumption_kwh = average_consumption_w / 1000.0

        return await get_estimate_discharge_time(
            station.battery_capacity,
            batt_soc,
            average_consumption_kwh,
        )

    def __str__(self):
        return "00:00"

