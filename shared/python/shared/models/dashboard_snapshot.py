"""Pydantic models for DashboardSnapshot v1."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from shared.models.dashboard_config import OutagesScheduleConfig
from shared.models.localizable_value import LocalizableValue
from shared.models.outages_schedule import UnitSchedule


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
    outages_schedule: Optional[OutagesScheduleConfig] = Field(
        None, alias="outagesSchedule"
    )

    model_config = ConfigDict(populate_by_name=True)


class DashboardSnapshot(BaseModel):
    epoch: int
    version: int
    generated_at: datetime = Field(alias="generatedAt")
    buildings: list[BuildingSnapshot]
    config: ConfigSnapshot
    outages_schedules: dict[str, UnitSchedule] = Field(alias="outagesSchedules")

    model_config = ConfigDict(populate_by_name=True)


__all__ = [
    "BuildingSnapshot",
    "ConfigSnapshot",
    "DashboardSnapshot",
]
