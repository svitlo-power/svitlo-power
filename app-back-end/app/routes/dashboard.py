from datetime import datetime, timezone
from typing import List, Optional
from beanie import PydanticObjectId
from fastapi import FastAPI, HTTPException, Request
from fastapi_injector import Injected
from pydantic import BaseModel, ConfigDict, Field

from shared.services import ReadOnlyDashboardService
from shared.services.dashboard_snapshot import DashboardSnapshotClient
from app.snapshot_mode import dashboard_snapshot_reads_enabled
from app.snapshot_responses import (
    snapshot_building_response,
    snapshot_building_summary_response,
    snapshot_building_with_summary_response,
)
from shared.models.localizable_value import LocalizableValue
from shared.models.api.dashboard import (
    BuildingResponse,
    BuildingSummaryResponse,
    BuildingWithSummaryResponse,
    BuildingsSummaryRequest,
    PowerLogsRequest,
    PowerLogsResponse
)


class AppDashboardConfigResponse(BaseModel):
    title: LocalizableValue
    enable_outages_schedule: bool = Field(False, alias="enableOutagesSchedule")
    outages_schedule_queue: Optional[str] = Field(None, alias="outagesScheduleQueue")

    model_config = ConfigDict(
        populate_by_name=True,
        from_attributes=True,
    )


def register(app: FastAPI):
  
    @app.get("/api/dashboard/buildings")
    async def get_buildings(
        request: Request,
        dashboard=Injected(ReadOnlyDashboardService),
        snapshot_client: DashboardSnapshotClient = Injected(DashboardSnapshotClient),
    ) -> List[BuildingResponse]:
        """Get list of buildings (basic info) - Android endpoint"""
        snapshot = snapshot_client.get_snapshot()
        if snapshot is not None:
            if (
                dashboard_snapshot_reads_enabled(request.app.state.settings)
                and not snapshot_client.is_stale
            ):
                return [snapshot_building_response(b) for b in snapshot.buildings]
        return await dashboard.get_buildings(all=False)

    @app.post("/api/dashboard/buildings/summary")
    async def get_buildings_summary(
        request: Request,
        body: BuildingsSummaryRequest,
        dashboard=Injected(ReadOnlyDashboardService),
        snapshot_client: DashboardSnapshotClient = Injected(DashboardSnapshotClient),
    ) -> List[BuildingSummaryResponse]:
        """Get building summaries (battery, grid status, etc.) - Android endpoint"""
        snapshot = snapshot_client.get_snapshot()
        if snapshot is not None:
            by_id = {building.id: building for building in snapshot.buildings}
            requested_ids = [str(building_id) for building_id in body.building_ids]
            if all(building_id in by_id for building_id in requested_ids):
                requested_ids_set = set(requested_ids)
                snapshot_response = lambda: [
                    snapshot_building_summary_response(building)
                    for building in snapshot.buildings
                    if building.id in requested_ids_set
                ]
                if (
                    dashboard_snapshot_reads_enabled(request.app.state.settings)
                    and not snapshot_client.is_stale
                ):
                    return snapshot_response()
        return await dashboard.get_buildings_summary(body.building_ids)

    @app.get("/api/buildings/buildings")
    async def get_buildings_data(
        request: Request,
        dashboard=Injected(ReadOnlyDashboardService),
        snapshot_client: DashboardSnapshotClient = Injected(DashboardSnapshotClient),
    ) -> List[BuildingWithSummaryResponse]:
        """Buildings with summary combined - Android endpoint (alias)"""
        snapshot = snapshot_client.get_snapshot()
        if snapshot is not None:
            snapshot_response = lambda: [
                snapshot_building_with_summary_response(b)
                for b in snapshot.buildings
            ]
            if (
                dashboard_snapshot_reads_enabled(request.app.state.settings)
                and not snapshot_client.is_stale
            ):
                return snapshot_response()
        return await dashboard.get_buildings_with_summary()

    @app.get("/api/dashboard/config")
    @app.get("/api/buildings/dashboardConfig")
    async def get_dashboard_config(
        request: Request,
        dashboard=Injected(ReadOnlyDashboardService),
        snapshot_client: DashboardSnapshotClient = Injected(DashboardSnapshotClient),
    ) -> AppDashboardConfigResponse:
        """Dashboard configuration (title, outages schedule) - Android endpoint"""

        snapshot = snapshot_client.get_snapshot()

        def snapshot_response():
            config = snapshot.config if snapshot else None
            schedule = config.outages_schedule if config else None
            return AppDashboardConfigResponse(
                title=config.title if config else {},
                enable_outages_schedule=bool(schedule and schedule.enable),
                outages_schedule_queue=schedule.queue if schedule else None,
            )

        async def legacy_response():
            config = await dashboard.get_config()
            schedule = config.outages_schedule
            return AppDashboardConfigResponse(
                title=config.title,
                enable_outages_schedule=bool(schedule and schedule.enable),
                outages_schedule_queue=schedule.queue if schedule else None,
            )

        if snapshot is not None:
            if (
                dashboard_snapshot_reads_enabled(request.app.state.settings)
                and not snapshot_client.is_stale
            ):
                return snapshot_response()
        return await legacy_response()

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