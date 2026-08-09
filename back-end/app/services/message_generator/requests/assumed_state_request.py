from dataclasses import dataclass
from typing import ClassVar
from injector import Injector

from ..models import TemplateRequest
from app.models import AssumedStationStatus
from app.repositories import IStationsDataRepository


@dataclass(frozen=True)
class AssumedStateRequest(TemplateRequest):
    name: ClassVar[str] = "get_assumed_state"

    station_id: int

    async def resolve(self, injector: Injector) -> float:
        stations_data = injector.get(IStationsDataRepository)
        return await stations_data.get_assumed_connection_status(self.station_id)

    def __str__(self):
        return AssumedStationStatus.NORMAL
