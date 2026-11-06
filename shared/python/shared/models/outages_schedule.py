from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List

from beanie import Document
from pydantic import BaseModel, Field, RootModel, model_validator


class OutagesSchedule(Document):
    """Outages schedule document for MongoDB."""

    queue: str
    data: dict
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "outages_schedule"
        indexes = ["queue"]


class SlotType(str, Enum):
    Definite = "Definite"
    NotPlanned = "NotPlanned"


class DayStatus(str, Enum):
    ScheduleApplies = "ScheduleApplies"
    EmergencyShutdowns = "EmergencyShutdowns"
    WaitingForSchedule = "WaitingForSchedule"
    NoOutages = "NoOutages"


class Slot(BaseModel):
    start: int
    end: int
    type: SlotType


class DaySchedule(BaseModel):
    slots: List[Slot]
    date: datetime
    status: DayStatus


class UnitSchedule(BaseModel):
    days: List[DaySchedule]
    updatedOn: datetime


def keep_only_definite_slots(schedule: "SchedulesResponse") -> "SchedulesResponse":
    for unit in schedule.root.values():
        for day in unit.days:
            day.slots = [
                slot for slot in day.slots if slot.type == SlotType.Definite
            ]
    return schedule


class SchedulesResponse(RootModel[Dict[str, UnitSchedule]]):
    @model_validator(mode="after")
    def clean_slots(self):
        return keep_only_definite_slots(self)
