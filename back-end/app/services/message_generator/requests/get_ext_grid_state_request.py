from dataclasses import dataclass
from injector import Injector
from typing import ClassVar

from ..models import TemplateRequest
from app.repositories import IExtDataRepository, IDashboardRepository


@dataclass(frozen=True)
class GetExtGridStateRequest(TemplateRequest):
    name: ClassVar[str] = "get_ext_grid_state"

    station_id: int

    async def resolve(self, injector: Injector) -> bool:
        ext_data_repo = injector.get(IExtDataRepository)
        buildings_repo = injector.get(IDashboardRepository)

        building = await buildings_repo.get_building_by_station_id(self.station_id)
        if building is None:
            return False

        state = False

        for reporter_user in building.report_users:
            reporter_state = await ext_data_repo.get_last_ext_data_by_user_id(reporter_user.id)
            if reporter_state and reporter_state.grid_state:
                state = True

        return state
