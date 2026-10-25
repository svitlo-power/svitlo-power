from datetime import datetime, timezone
from typing import List
from beanie import PydanticObjectId
from fastapi import FastAPI, Depends, HTTPException
from fastapi_injector import Injected
from pydantic import BaseModel, ConfigDict, Field

from app.services import DashboardService
from app.utils.jwt_dependencies import get_current_jwt_optional, jwt_required
from app.models.api import SaveBuildingRequest, PowerLogsRequest, PowerLogsResponse
from shared.models.api.dashboard import (
    BuildingResponse,
    BuildingSummaryResponse,
    BuildingWithSummaryResponse,
    BuildingsSummaryRequest,
    DashboardConfigResponse,
    EditBuildingResponse,
    SaveDashboardConfigRequest,
)
from shared.models.localizable_value import LocalizableValue


class LegacyDashboardConfigResponse(BaseModel):
    title: LocalizableValue
    enable_outages_schedule: bool = Field(alias="enableOutagesSchedule")
    outages_schedule_queue: str | None = Field(alias="outagesScheduleQueue")

    model_config = ConfigDict(populate_by_name=True)


def register(app: FastAPI):

    @app.get("/api/dashboard/buildings")
    async def get_buildings(
        dashboard = Injected(DashboardService),
        current_claims: dict | None = Depends(get_current_jwt_optional),
    ) -> List[BuildingResponse]:
        all = current_claims.get("sub", False) is not None if current_claims else False
        return await dashboard.get_buildings(all=all)


    @app.post("/api/dashboard/buildings/summary")
    async def get_buildings_summary(
        body: BuildingsSummaryRequest,
        dashboard = Injected(DashboardService),
    ) -> List[BuildingSummaryResponse]:
        return await dashboard.get_buildings_summary(body.building_ids)


    @app.get("/api/buildings/buildings")
    async def get_buildings_data(
        dashboard = Injected(DashboardService),
    ) -> List[BuildingWithSummaryResponse]:
        return await dashboard.get_buildings_with_summary()


    @app.get("/api/buildings/dashboardConfig")
    async def get_legacy_dashboard_config(
        dashboard = Injected(DashboardService),
    ) -> LegacyDashboardConfigResponse:
        configs = await dashboard.get_config()
        return LegacyDashboardConfigResponse(
            title=configs.title,
            enable_outages_schedule=configs.enable_outages_schedule,
            outages_schedule_queue=configs.outages_schedule_queue,
        )


    @app.get("/api/dashboard/config")
    async def get_dashboard_config(
        dashboard = Injected(DashboardService),
    ) -> DashboardConfigResponse:
        return await dashboard.get_config()


    @app.put("/api/dashboard/config")
    async def update_dashboard_config(
        body: SaveDashboardConfigRequest,
        _ = Depends(jwt_required),
        dashboard = Injected(DashboardService),
    ):
        return await dashboard.save_config(body)


    @app.get("/api/dashboard/buildings/{building_id}")
    async def get_building(
        building_id: PydanticObjectId,
        _ = Depends(jwt_required),
        dashboard = Injected(DashboardService),
    ) -> EditBuildingResponse:
        building = await dashboard.get_building(building_id)
        if not building:
            raise HTTPException(status_code=404, detail="Building not found")
        return building


    @app.put("/api/dashboard/buildings/{building_id}")
    async def edit_building(
        building_id: PydanticObjectId,
        body: SaveBuildingRequest,
        _ = Depends(jwt_required),
        dashboard = Injected(DashboardService),
    ):
        await dashboard.edit_building(building_id, body)
        return { "success": True, "id": str(building_id) }


    @app.post("/api/dashboard/buildings")
    async def create_building(
        body: SaveBuildingRequest,
        _ = Depends(jwt_required),
        dashboard = Injected(DashboardService),
    ):
        building_id = await dashboard.create_building(body)
        return { "success": True, "id": str(building_id) }


    @app.delete("/api/dashboard/buildings/{building_id}")
    async def delete_building(
        building_id: PydanticObjectId,
        _ = Depends(jwt_required),
        dashboard = Injected(DashboardService),
    ):
        result = await dashboard.delete_building(building_id)
        return { "success": result, "id": str(building_id) }


    @app.post("/api/dashboard/buildings/{building_id}/power-logs")
    @app.post("/api/buildings/{building_id}/power-logs")
    async def get_building_power_logs(
        building_id: PydanticObjectId,
        body: PowerLogsRequest,
        dashboard = Injected(DashboardService),
    ) -> PowerLogsResponse:
        try:
            start_date = datetime.fromisoformat(body.start_date.replace("Z", "+00:00"))
            end_date = datetime.fromisoformat(body.end_date.replace("Z", "+00:00"))

            start_date = start_date.replace(tzinfo=timezone.utc) if start_date.tzinfo is None else start_date
            end_date = end_date.replace(tzinfo=timezone.utc) if end_date.tzinfo is None else end_date

            if start_date >= end_date:
                raise HTTPException(status_code=400, detail="startDate must be before endDate")
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid date format: {str(e)}")

        power_logs = await dashboard.get_power_logs(building_id, start_date, end_date)
        if not power_logs:
            raise HTTPException(status_code=404, detail="Building not found or no power logs available")

        return power_logs
