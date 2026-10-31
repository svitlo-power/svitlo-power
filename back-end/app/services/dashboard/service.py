import asyncio
from beanie import PydanticObjectId
from injector import inject

from shared.models.assumed_station_status import AssumedStationStatus
from shared.models.building import Building
from shared.services.events.service import EventsService
from shared.services.dashboard import ReadOnlyDashboardService
from shared.features import feature_flags, FeatureFlag
from app.repositories import (
    IDashboardRepository,
    IExtDataRepository,
    IStationsRepository,
    IStationsDataRepository,
    IUsersRepository,
)
from app.models.api import (
    DashboardConfigResponse,
    SaveBuildingRequest,
    SaveDashboardConfigRequest,
)
from shared.services.settings.service import SettingsService
from shared.services.dashboard.config_settings import (
    DASHBOARD_TITLE_SETTING_KEY,
    DASHBOARD_OUTAGES_SCHEDULE_ENABLED_SETTING_KEY,
    DASHBOARD_OUTAGES_SCHEDULE_REGION_SETTING_KEY,
    DASHBOARD_OUTAGES_SCHEDULE_DSO_SETTING_KEY,
    DASHBOARD_OUTAGES_SCHEDULE_QUEUE_SETTING_KEY,
)
from app.services.dashboard_snapshot.service import DashboardSnapshotService


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
        settings: SettingsService,
        snapshot_service: DashboardSnapshotService,
    ):
        super().__init__(
            events=events,
            dashboard=dashboard,
            ext_data=ext_data,
            stations=stations,
            stations_data=stations_data,
            users=users,
            settings=settings,
        )
        self._snapshot_service = snapshot_service
    
    def _should_publish_snapshot(self) -> bool:
        """Check if dashboard snapshot publishing is enabled via feature flag."""
        return feature_flags.is_enabled(FeatureFlag.DASHBOARD_SNAPSHOT_PUBLISH)
    
    async def _broadcast_if_enabled(self, event_type: str, data: dict = None):
        """Broadcast event only if snapshot publishing is enabled."""
        if self._should_publish_snapshot():
            await self.broadcast_public(event_type, data)

    async def _refresh_snapshot_if_enabled(self) -> None:
        """Refresh dashboard snapshot if publishing is enabled."""
        if self._should_publish_snapshot():
            await self._snapshot_service.refresh_and_publish()

    async def save_config(self, config: SaveDashboardConfigRequest) -> DashboardConfigResponse:
        schedule = config.outages_schedule
        updates = {
            DASHBOARD_TITLE_SETTING_KEY: config.title,
            DASHBOARD_OUTAGES_SCHEDULE_ENABLED_SETTING_KEY: bool(
                schedule and schedule.enable
            ),
        }
        if schedule and schedule.enable:
            updates.update({
                DASHBOARD_OUTAGES_SCHEDULE_REGION_SETTING_KEY: schedule.region_id,
                DASHBOARD_OUTAGES_SCHEDULE_DSO_SETTING_KEY: schedule.dso_id,
                DASHBOARD_OUTAGES_SCHEDULE_QUEUE_SETTING_KEY: schedule.queue,
            })
        results = await self._settings.bulk_update(updates)
        failed_settings = [key for key in updates if not results.get(key, False)]
        if failed_settings:
            raise RuntimeError(
                f"Unable to save dashboard settings: {', '.join(failed_settings)}"
            )
        await self._broadcast_if_enabled("dashboard_config_updated")
        await self._refresh_snapshot_if_enabled()
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
            await self._broadcast_if_enabled("buildings_updated")
            await self._refresh_snapshot_if_enabled()
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
        await self._broadcast_if_enabled("buildings_updated")
        await self._refresh_snapshot_if_enabled()
        return building_id

    async def delete_building(self, building_id: PydanticObjectId) -> bool:
        building = await self._dashboard.get_building(building_id)
        if building:
            await self._dashboard.delete_building(building)
            remaining_buildings = await self._dashboard.get_buildings(all=True)
            await self._dashboard.reorder_buildings(remaining_buildings)
            await self._broadcast_if_enabled("buildings_updated")
            await self._refresh_snapshot_if_enabled()
            return True
        return False
