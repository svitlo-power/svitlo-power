from datetime import datetime, timedelta, timezone
from dataclasses import dataclass
from typing import ClassVar
from injector import Injector

from ..models import NumericTemplateRequest
from app.repositories import IStationsDataRepository


@dataclass(frozen=True)
class AverageMinutesRequest(NumericTemplateRequest):
    name: ClassVar[str] = "get_average_minutes"

    station_id: int
    column: str
    minutes: int

    async def resolve(self, injector: Injector) -> float:
        stations_data = injector.get(IStationsDataRepository)
        now = datetime.now(timezone.utc)
        return await stations_data.get_station_data_average_column(
            start_date  = now - timedelta(minutes=self.minutes),
            end_date    = now,
            station_id  = self.station_id,
            column_name = self.column,
        )