from datetime import datetime, timezone
from typing import List, Optional
from beanie import PydanticObjectId
from fastapi import FastAPI, HTTPException
from fastapi_injector import Injected
from pydantic import BaseModel, ConfigDict, Field

from shared.services import ReadOnlyDashboardService
from shared.features import feature_flags, FeatureFlag
from shared.models.localizable_value import LocalizableValue
from shared.models.api.dashboard import (
    BuildingResponse,
    BuildingSummaryResponse,
    BuildingWithSummaryResponse,
    BuildingsSummaryRequest,
    PowerLogsRequest,
    PowerLogsResponse
)
from app.clients.dashboard_snapshot_client import DashboardSnapshotClient


class AppDashboardConfigResponse(BaseModel):
    title: LocalizableValue
    enable_outages_schedule: bool = Field(False, alias="enableOutagesSchedule")
    outages_schedule_queue: Optional[str] = Field(None, alias="outagesScheduleQueue")

    model_config = ConfigDict(
        populate_by_name=True,
        from_attributes=True,
    )


def _is_redis_reads_enabled() -> bool:
    return feature_flags.is_enabled(FeatureFlag.APP_BACKEND_REDIS_READS)


def _building_from_snapshot(building) -> BuildingResponse:
    return BuildingResponse(
        id=building.id,
        name=building.name,
        color=building.color,
        has_bound_station=building.has_bound_station,
        order=building.order,
    )


def _summary_from_snapshot(building) -> BuildingSummaryResponse:
    return BuildingSummaryResponse(
        id=building.id,
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


def _with_summary_from_snapshot(building) -> BuildingWithSummaryResponse:
    return BuildingWithSummaryResponse(
        id=building.id,
        name=building.name,
        color=building.color,
        has_bound_station=building.has_bound_station,
        order=building.order,
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


def register(app: FastAPI):
  
    @app.get("/api/dashboard/buildings")
    async def get_buildings(
            dashboard=Injected(ReadOnlyDashboardService),
            snapshot_client=Injected(DashboardSnapshotClient),
        ) -> List[BuildingResponse]:
            """Get list of buildings (basic info) - Android endpoint"""
            if _is_redis_reads_enabled():
                buildings = snapshot_client.get_buildings()
                return [_building_from_snapshot(b) for b in buildings]
            return await dashboard.get_buildings(all=False)

    @app.post("/api/dashboard/buildings/summary")
    async def get_buildings_summary(
        body: BuildingsSummaryRequest,
            dashboard=Injected(ReadOnlyDashboardService),
            snapshot_client=Injected(DashboardSnapshotClient),
        ) -> List[BuildingSummaryResponse]:
            """Get building summaries (battery, grid status, etc.) - Android endpoint"""
            if _is_redis_reads_enabled():
                buildings = snapshot_client.get_buildings()
                id_set = set(body.building_ids)
                result = []
                for b in buildings:
                    # building.id is a string in the snapshot
                    from beanie import PydanticObjectId
                    try:
                        bid = PydanticObjectId(b.id)
                    except Exception:
                        continue
                    if bid in id_set:
                        result.append(_summary_from_snapshot(b))
                return result
            return await dashboard.get_buildings_summary(body.building_ids)

    @app.get("/api/buildings/buildings")
    async def get_buildings_data(
            dashboard=Injected(ReadOnlyDashboardService),
            snapshot_client=Injected(DashboardSnapshotClient),
        ) -> List[BuildingWithSummaryResponse]:
            """Buildings with summary combined - Android endpoint (alias)"""
            if _is_redis_reads_enabled():
                buildings = snapshot_client.get_buildings()
                return [_with_summary_from_snapshot(b) for b in buildings]
            return await dashboard.get_buildings_with_summary()

    @app.get("/api/dashboard/config")
    @app.get("/api/buildings/dashboardConfig")
    async def get_dashboard_config(
            dashboard=Injected(ReadOnlyDashboardService),
            snapshot_client=Injected(DashboardSnapshotClient),
        ) -> AppDashboardConfigResponse:
            """Dashboard configuration (title, outages schedule) - Android endpoint"""
            if _is_redis_reads_enabled():
                config = snapshot_client.get_config()
                if config is None:
                    # Fall back to legacy
                    config = await dashboard.get_config()
                    schedule = config.outages_schedule
                    return AppDashboardConfigResponse(
                        title=config.title,
                        enable_outages_schedule=bool(schedule and schedule.enable),
                        outages_schedule_queue=schedule.queue if schedule else None,
                    )
                schedule = config.outages_schedule
                return AppDashboardConfigResponse(
                    title=config.title,
                    enable_outages_schedule=bool(schedule and schedule.get("enable")),
                    outages_schedule_queue=schedule.get("queue") if schedule else None,
                )
            config = await dashboard.get_config()
            schedule = config.outages_schedule
            return AppDashboardConfigResponse(
                title=config.title,
                enable_outages_schedule=bool(schedule and schedule.enable),
                outages_schedule_queue=schedule.queue if schedule else None,
            )

    @app.post("/api/dashboard/buildings/{building_id}/power-logs")
    @app.post("/api/buildings/{building_id}/power-logs")
    async def get_building_power_logs(
        building_id: PydanticObjectId,
        body: PowerLogsRequest,
            dashboard=Injected(ReadOnlyDashboardService),
        ) -> PowerLogsResponse:
            """Power logs for a building (date range) - Android endpoint"""
            try:
                start_date = datetime.fromisoformat(body.start_date.replace("Z", "+00:00"))
                end_date = datetime.fromisoformat(body.end_date.replace("Z", "+00:00"))

                start_date = start_date.replace(tzinfo=timezone.utc) if start_date.tzinfo is None else start_date
                end_date = end_date.replace(tzinfo=timezone.utc) if end_date.tzinfo is None else end_date

                if start_date >= end_date:
                    raise HTTPException(status_code=400, detail="startDate must be before endDate")
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Invalid date format: {str(e)}")

            power_logs = await dashboard.get_power_logs(building_id, start_date, end_date)
            if not power_logs:
                raise HTTPException(status_code=404, detail="Building not found or no power logs available")

            return power_logs