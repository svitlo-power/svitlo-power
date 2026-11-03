"""Outage schedule types shared between back-end and app-back-end.

Reused by shared/models/snapshot.py.
"""

from datetime import datetime
from typing import List
from pydantic import BaseModel, ConfigDict
from enum import Enum


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

    model_config = ConfigDict(populate_by_name=True)


class DaySchedule(BaseModel):
    slots: List[Slot]
    date: datetime
    status: DayStatus

    model_config = ConfigDict(populate_by_name=True)


class UnitSchedule(BaseModel):
    days: List[DaySchedule]
    updatedOn: datetime

    model_config = ConfigDict(populate_by_name=True)

__all__ = [
    "SlotType",
    "DayStatus",
    "Slot",
    "DaySchedule",
    "UnitSchedule",
]
