"""Pydantic models for DashboardSnapshot v1 schema.

Matches docs/architecture/snapshot-schema.json.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class SlotSnapshot(BaseModel):
    start: int = Field(..., description="Minutes from midnight")
    end: int = Field(..., description="Minutes from midnight")
    type: str = Field(..., description="Definite or NotPlanned")

    model_config = ConfigDict(populate_by_name=True)


class DayScheduleSnapshot(BaseModel):
    slots: list[SlotSnapshot]
    date: datetime
    status: str = Field(
        ...,
        description="ScheduleApplies, EmergencyShutdowns, WaitingForSchedule, NoOutages",
    )

    model_config = ConfigDict(populate_by_name=True)


class UnitScheduleSnapshot(BaseModel):
    days: list[DayScheduleSnapshot]
    updatedOn: datetime

    model_config = ConfigDict(populate_by_name=True)


class LocalizableValue(BaseModel):
    uk: str
    en: str

    model_config = ConfigDict(populate_by_name=True)


class BuildingSnapshot(BaseModel):
    id: str = Field(..., pattern=r"^[0-9a-f]{24}$")
    name: LocalizableValue
    color: str
    order: int
    has_bound_station: bool = Field(alias="hasBoundStation")
    is_grid_available: Optional[bool] = Field(None, alias="isGridAvailable")
    grid_availability_pct: Optional[int] = Field(None, alias="gridAvailabilityPct")
    has_mixed_reporter_states: Optional[bool] = Field(
        None, alias="hasMixedReporterStates"
    )
    is_charging: Optional[bool] = Field(None, alias="isCharging")
    is_discharging: Optional[bool] = Field(None, alias="isDischarging")
    is_offline: Optional[bool] = Field(None, alias="isOffline")
    battery_percent: Optional[float] = Field(None, alias="batteryPercent")
    consumption_power: Optional[str] = Field(None, alias="consumptionPower")
    battery_discharge_time: Optional[str] = Field(
        None, alias="batteryDischargeTime"
    )
    battery_charge_time: Optional[str] = Field(None, alias="batteryChargeTime")
    charge_source: str = Field(alias="chargeSource")
    charge_power: Optional[float] = Field(None, alias="chargePower")

    model_config = ConfigDict(populate_by_name=True)


class ConfigSnapshot(BaseModel):
    title: LocalizableValue
    outages_schedule: Optional[dict] = Field(None, alias="outagesSchedule")

    model_config = ConfigDict(populate_by_name=True)


class DashboardSnapshot(BaseModel):
    epoch: int
    version: int
    generated_at: datetime = Field(alias="generatedAt")
    buildings: list[BuildingSnapshot]
    config: ConfigSnapshot
    outages_schedules: dict[str, UnitScheduleSnapshot] = Field(
        alias="outagesSchedules"
    )

    model_config = ConfigDict(populate_by_name=True)
