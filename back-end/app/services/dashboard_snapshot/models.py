"""Backward-compatible imports for the shared DashboardSnapshot v1 schema."""

from shared.models.dashboard_snapshot import (
    BuildingSnapshot,
    ConfigSnapshot,
    DashboardSnapshot,
    DayScheduleSnapshot,
    LocalizableValue,
    SlotSnapshot,
    UnitScheduleSnapshot,
)

__all__ = [
    "BuildingSnapshot",
    "ConfigSnapshot",
    "DashboardSnapshot",
    "DayScheduleSnapshot",
    "LocalizableValue",
    "SlotSnapshot",
    "UnitScheduleSnapshot",
]
