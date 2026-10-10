import asyncio
from datetime import datetime, timedelta, timezone
from typing import List
from beanie import PydanticObjectId
from injector import inject

from shared.models.assumed_station_status import AssumedStationStatus
from shared.models.building import Building
from shared.models.dashboard_config import DashboardConfig
from shared.models.ext_data import ExtData
from shared.services.events.service import EventsService
from shared.services.dashboard import ReadOnlyDashboardService
from app.repositories import (
    IDashboardRepository,
    IExtDataRepository,
    IStationsRepository,
    IStationsDataRepository,
    IUsersRepository,
)
from app.models.api import (
    BuildingResponse,
    BuildingSummaryResponse,
    BuildingWithSummaryResponse,
    ChargeSource,
    DashboardConfigResponse,
    EditBuildingResponse,
    PeriodResponse,
    PowerLogsResponse,
    SaveBuildingRequest,
    SaveDashboardConfigRequest,
)
from app.utils import get_estimate_charge_time, get_estimate_discharge_time


@inject
class DashboardService(ReadOnlyDashboardService):
    def __init__(
        self,
        events: EventsService,
        dashboard: IDashboardRepository,
        ext_data: IExtDataRepository,
        stations: IStationsRepository,
        stations_data: IStationsDataRepository,
        users: IUsersRepository,
    ):
        super().__init__(
            events=events,
            dashboard=dashboard,
            ext_data=ext_data,
            stations=stations,
            stations_data=stations_data,
            users=users,
        )

    async def save_config(self, config: SaveDashboardConfigRequest) -> DashboardConfigResponse:
        config = DashboardConfig(
            title=config.title,
            enable_outages_schedule=config.enable_outages_schedule,
            outages_schedule_queue=config.outages_schedule_queue,
        )
        await self._dashboard.save_config(config)
        await self.broadcast_public("dashboard_config_updated")
        return await self.get_config()

    async def edit_building(
        self,
        building_id: PydanticObjectId,
        request: SaveBuildingRequest,
    ) -> PydanticObjectId:
        building = await self._dashboard.get_building(building_id)
        if building:
            station = await self._stations.get_station(request.station_id) if request.station_id else None
            users = await asyncio.gather(
                *[self._users.get_user_by_id(user_id) for user_id in request.report_user_ids]
            ) if request.report_user_ids else None

            building.name = request.name
            building.color = request.color
            building.station = station
            building.report_users = users
            building.enabled = request.enabled
            building.order = request.order

            await self._dashboard.edit_building(building)
            await self.broadcast_public("buildings_updated")
            return building_id

        return None

    async def create_building(self, request: SaveBuildingRequest) -> PydanticObjectId:
        station = await self._stations.get_station(request.station_id) if request.station_id else None
        users = await asyncio.gather(
            *[self._users.get_user_by_id(user_id) for user_id in request.report_user_ids]
        ) if request.report_user_ids else []

        building = Building(
            name=request.name,
            color=request.color,
            station=station,
            report_users=users,
            enabled=request.enabled,
            order=request.order,
        )

        building_id = await self._dashboard.create_building(building)
        await self.broadcast_public("buildings_updated")
        return building_id

    async def delete_building(self, building_id: PydanticObjectId) -> bool:
        building = await self._dashboard.get_building(building_id)
        if building:
            await self._dashboard.delete_building(building)
            remaining_buildings = await self._dashboard.get_buildings(all=True)
            await self._dashboard.reorder_buildings(remaining_buildings)
            await self.broadcast_public("buildings_updated")
            return True
        return False
