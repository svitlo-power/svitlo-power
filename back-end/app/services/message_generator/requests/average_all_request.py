from datetime import datetime, timezone
from dataclasses import dataclass
from typing import ClassVar
from injector import Injector

from ..models import NumericTemplateRequest
from app.repositories import IStationsDataRepository


@dataclass(frozen=True)
class AverageAllRequest(NumericTemplateRequest):
    name: ClassVar[str] = "get_average_all"

    station_id: int
    column: str

    async def resolve(self, injector: Injector) -> float:
        stations_data = injector.get(IStationsDataRepository)
        now = datetime.now(timezone.utc)
        return await stations_data.get_station_data_average_column(
            start_date  = self.start_date,
            end_date    = now,
            station_id  = self.station_id,
            column_name = self.column,
        )

