"""Outage schedule service models.

Reuses Slot, DaySchedule, UnitSchedule from shared/models/schedule_types.py.
"""

from typing import Dict
from datetime import datetime
from pydantic import BaseModel, RootModel, model_validator
from enum import Enum

from shared.models.schedule_types import (
    SlotType,
    DayStatus,
    Slot,
    DaySchedule,
    UnitSchedule,
)


def keep_only_definite_slots(schedule: "SchedulesResponse") -> "SchedulesResponse":
    for unit in schedule.root.values():
        for day in unit.days:
            day.slots = [s for s in day.slots if s.type == SlotType.Definite]
    return schedule


class SchedulesResponse(RootModel[Dict[str, UnitSchedule]]):
    pass

    @model_validator(mode="after")
    def clean_slots(cls, model):
        return keep_only_definite_slots(model)