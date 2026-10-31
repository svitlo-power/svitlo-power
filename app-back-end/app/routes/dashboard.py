from datetime import datetime, timezone
from typing import List, Optional
from beanie import PydanticObjectId
from fastapi import FastAPI, HTTPException
from fastapi_injector import Injected
from pydantic import BaseModel, ConfigDict, Field

from shared.services import ReadOnlyDashboardService
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
            dashboard=Injected(ReadOnlyDashboardService),
        ) -> List[BuildingResponse]:
            """Get list of buildings (basic info) - Android endpoint"""
            return await dashboard.get_buildings(all=False)

    @app.post("/api/dashboard/buildings/summary")
    async def get_buildings_summary(
        body: BuildingsSummaryRequest,
            dashboard=Injected(ReadOnlyDashboardService),
        ) -> List[BuildingSummaryResponse]:
            """Get building summaries (battery, grid status, etc.) - Android endpoint"""
            return await dashboard.get_buildings_summary(body.building_ids)

    @app.get("/api/buildings/buildings")
    async def get_buildings_data(
            dashboard=Injected(ReadOnlyDashboardService),
        ) -> List[BuildingWithSummaryResponse]:
            """Buildings with summary combined - Android endpoint (alias)"""
            return await dashboard.get_buildings_with_summary()

    @app.get("/api/dashboard/config")
    @app.get("/api/buildings/dashboardConfig")
    async def get_dashboard_config(
            dashboard=Injected(ReadOnlyDashboardService),
        ) -> AppDashboardConfigResponse:
            """Dashboard configuration (title, outages schedule) - Android endpoint"""
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