from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import ClassVar
from injector import Injector

from ..models import TemplateRequest
from app.repositories import IStationsRepository, IStationsDataRepository
from shared.services import SettingsService
from shared.utils import get_estimate_discharge_time


@dataclass(frozen=True)
class EstimateDischargeTimeRequest(TemplateRequest):
    name: ClassVar[str] = "get_estimate_discharge_time"

    # Station document id (StationData.station_id), not the external Deye station_id
    station_id: int

    async def resolve(self, injector: Injector) -> str:
        stations_repo = injector.get(IStationsRepository)
        stations_data_repo = injector.get(IStationsDataRepository)
        settings = injector.get(SettingsService)

        station = await stations_repo.get_station(str(self.station_id))
        if station is None or station.battery_capacity is None:
            return "00:00"

        station_data = await stations_data_repo.get_last_station_data(station.id)
        if station_data is None:
            return "00:00"

        batt_soc = station_data.battery_soc
        if batt_soc is None:
            return "00:00"

        minutes = await settings.get_number("estimate_discharge_period_minutes", 25)
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(minutes=minutes)

        average_consumption_w = await stations_data_repo.get_station_data_average_column(
            start_date=start_date,
            end_date=end_date,
            station_id=station.id,
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
