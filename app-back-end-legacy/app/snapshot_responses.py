"""Convert shared snapshot models to the existing mobile API response models."""

from beanie import PydanticObjectId

from shared.models.api.dashboard import (
    BuildingResponse,
    BuildingSummaryResponse,
    BuildingWithSummaryResponse,
)
from shared.models.dashboard_snapshot import BuildingSnapshot


def snapshot_building_response(building: BuildingSnapshot) -> BuildingResponse:
    return BuildingResponse(
        id=PydanticObjectId(building.id),
        name=building.name,
        color=building.color,
        has_bound_station=building.has_bound_station,
        order=building.order,
    )


def snapshot_building_summary_response(
    building: BuildingSnapshot,
) -> BuildingSummaryResponse:
    return BuildingSummaryResponse(
        id=PydanticObjectId(building.id),
        is_grid_available=building.is_grid_available,
        grid_availability_pct=building.grid_availability_pct,
        has_mixed_reporter_states=building.has_mixed_reporter_states,
        is_charging=building.is_charging,
        is_discharging=building.is_discharging,
        is_offline=building.is_offline,
        battery_percent=building.battery_percent,
        consumption_power=building.consumption_power,
        battery_discharge_time=building.battery_discharge_time,
        battery_charge_time=building.battery_charge_time,
        charge_source=building.charge_source,
        charge_power=building.charge_power,
    )


def snapshot_building_with_summary_response(
    building: BuildingSnapshot,
) -> BuildingWithSummaryResponse:
    summary = snapshot_building_summary_response(building)
    return BuildingWithSummaryResponse(
        **summary.model_dump(),
        name=building.name,
        color=building.color,
        has_bound_station=building.has_bound_station,
        order=building.order,
    )
