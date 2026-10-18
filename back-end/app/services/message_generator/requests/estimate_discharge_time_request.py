from dataclasses import dataclass
from injector import Injector

from ..models import TemplateRequest


@dataclass(frozen=True)
class EstimateDischargeTimeRequest(TemplateRequest):
    batt_capacity_kwh: float
    batt_soc: int
    average_consumption_kwh: float

    async def resolve(self, _: Injector) -> str:
        from app.utils import get_estimate_discharge_time
        return await get_estimate_discharge_time(
            self.batt_capacity_kwh,
            self.batt_soc,
            self.average_consumption_kwh,
        )
    
    def __str__(self):
        return "00:00"

