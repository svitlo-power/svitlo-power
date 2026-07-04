import asyncio
from datetime import datetime, timedelta, timezone
from typing import List
from beanie import PydanticObjectId
from injector import inject

from shared.models.building import Building
from shared.models.dashboard_config import DashboardConfig
from shared.models.ext_data import ExtData
from shared.services.events.service import EventsService
from ..base import BaseService
from app.repositories import (
    IDashboardRepository,
    IExtDataRepository,
    IStationsRepository,
    IStationsDataRepository,
    IUsersRepository,
)
from app.models import AssumedStationStatus
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
class DashboardService(BaseService):
    def __init__(
        self,
        events: EventsService,
        dashboard: IDashboardRepository,
        ext_data: IExtDataRepository,
        stations: IStationsRepository,
        stations_data: IStationsDataRepository,
        users: IUsersRepository,
    ):
        super().__init__(events)
        self._dashboard = dashboard
        self._ext_data = ext_data
        self._stations = stations
        self._stations_data = stations_data
        self._users = users


    async def get_config(self) -> DashboardConfigResponse:
        config = await self._dashboard.get_config()
        return DashboardConfigResponse(
            title                   = config.title,
            enable_outages_schedule = config.enable_outages_schedule,
            outages_schedule_queue  = config.outages_schedule_queue,
        )


    async def save_config(self, config: SaveDashboardConfigRequest) -> DashboardConfigResponse:
        config = DashboardConfig(
            title                   = config.title,
            enable_outages_schedule = config.enable_outages_schedule,
            outages_schedule_queue  = config.outages_schedule_queue,
        )
        await self._dashboard.save_config(config)
        await self.broadcast_public("dashboard_config_updated")
        return await self.get_config()


    def _process_building(self, building: Building) -> BuildingResponse:
        return BuildingResponse(
            id                = building.id,
            color             = building.color,
            name              = building.name,
            has_bound_station = building.station is not None,
            order             = building.order,
        )


    async def get_building(self, building_id: PydanticObjectId) -> EditBuildingResponse:
        building = await self._dashboard.get_building(building_id)
        response = self._process_building(building)
        return EditBuildingResponse(
            **response.model_dump(),
            report_user_ids = [user.id for user in building.report_users],
            station_id      = building.station.id if building.station else None,
            enabled         = building.enabled,
        )


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
        ) if request.report_user_ids else None

        building = Building(
            name         = request.name,
            color        = request.color,
            station      = station,
            report_users = users,
            enabled      = request.enabled,
            order        = request.order,
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


    async def get_buildings(self, all: bool = False) -> List[BuildingResponse]:
        buildings = await self._dashboard.get_buildings(all=all)
        return [self._process_building(building) for building in buildings]


    async def _process_building_summary(self, building: Building, minutes) -> BuildingSummaryResponse:
        result = BuildingSummaryResponse(
            id    = building.id
        )

        ext_datas: List[ExtData] = await asyncio.gather(
            *(self._ext_data.get_last_ext_data_by_user_id(report_user.id)
                for report_user in building.report_users)
        )
        if ext_datas and len(ext_datas) > 0:
            result.is_grid_available = any(x and x.grid_state for x in ext_datas)
            true_count = sum(x.grid_state for x in ext_datas if x)
            result.grid_availability_pct = int((true_count / len(ext_datas)) * 100)
            result.has_mixed_reporter_states = (
                true_count > 0 and true_count < len(ext_datas)
            )

        if building.station:
            station_id = building.station.id
            station_data = await self._stations_data.get_last_station_data(station_id)
            if station_data is None:
                return result

            is_discharging = (station_data.discharge_power or 0) > 200
            is_charging = (station_data.charge_power or 0) * -1 > 200

            assumed_offline = await self._stations_data.get_assumed_connection_status(station_id) == AssumedStationStatus.OFFLINE
            result.is_offline = building.station.connection_status == 'ALL_OFFLINE' or assumed_offline
            result.is_charging = is_charging
            result.is_discharging = is_discharging
            result.battery_percent = station_data.battery_soc

            average_consumption_w = await self._stations_data.get_station_data_average_column(
                datetime.now(timezone.utc) - timedelta(minutes=minutes),
                datetime.now(timezone.utc),
                station_id,
                "consumption_power",
            ) or 0

            result.consumption_power = f"{(average_consumption_w / 1000):.2f}"

            batt_capacity = building.station.battery_capacity
            batt_soc = station_data.battery_soc
            if is_charging and (station_data.charge_power or 0) != 0:
                result.charge_source = ChargeSource.GRID
                if (station_data.generation_power or 0) > 0 and (station_data.wire_power or 0) == 0:
                    result.charge_source = ChargeSource.GENERATOR
                if (station_data.generation_power or 0) == 0 and (station_data.wire_power or 0) == 0:
                    result.charge_source = ChargeSource.RECUPERATION
                result.battery_charge_time = get_estimate_charge_time(
                    batt_capacity,
                    batt_soc,
                    ((station_data.charge_power or 0) / 1000.0) * -1,
                    97,
                )
                result.charge_power = ((station_data.charge_power or 0) * -1) / 1000.0

            if is_discharging and average_consumption_w > 0:
                estimate_discharge_time = get_estimate_discharge_time(
                    batt_capacity,
                    batt_soc,
                    average_consumption_w / 1000,
                    10
                )
                result.battery_discharge_time = estimate_discharge_time

        return result


    async def get_buildings_summary(self, building_ids: List[PydanticObjectId]) -> List[BuildingSummaryResponse]:
        buildings = await self._dashboard.get_buildings(building_ids)
        minutes = 25

        return await asyncio.gather(
            *(self._process_building_summary(b, minutes) for b in buildings)
        )


    async def get_buildings_with_summary(self) -> List[BuildingWithSummaryResponse]:
        buildings = await self._dashboard.get_buildings()
        minutes = 25

        async def process_building(building: Building) -> BuildingWithSummaryResponse:
            res = await self._process_building_summary(building, minutes)

            return BuildingWithSummaryResponse(
                **res.model_dump(),
                name  = building.name,
                color = building.color,
            )

        return [await process_building(b) for b in buildings]


    async def _compute_total_generator_time(
        self,
        station_id: str,
        start_date: datetime,
        end_date: datetime,
    ) -> int:
        data = await self._stations_data.get_full_station_data_range(
            station_id,
            start_date,
            end_date,
        )
        if data and len(data) > 1:
            total_seconds = 0
            for i in range(1, len(data)):
                prev = data[i - 1]
                curr = data[i]

                if (prev.charge_power or 0) * -1 > 200 and (prev.generation_power or 0) > 0 and (prev.wire_power or 0) == 0:
                    delta = (curr.last_update_time - prev.last_update_time).total_seconds()
                    total_seconds += delta

            return total_seconds
        return 0


    async def get_power_logs(
        self,
        building_id: PydanticObjectId,
        start_date: datetime,
        end_date: datetime,
    ) -> PowerLogsResponse:
        building = await self._dashboard.get_building(building_id)
        if not building:
            return None

        if not building.report_users or len(building.report_users) == 0:
            return None

        all_records_by_user = await asyncio.gather(
            *(self._ext_data.get_ext_data_statistics(report_user.id, start_date, end_date)
              for report_user in building.report_users)
        )

        last_before_by_user = await asyncio.gather(
            *(self._ext_data.get_last_ext_data_before_date(report_user.id, start_date)
              for report_user in building.report_users)
        )

        total_generator_seconds = await self._compute_total_generator_time(
            building.station.id,
            start_date,
            end_date
        ) if building.station else 0

        all_events = []

        for user_idx, records in enumerate(all_records_by_user):
            if records:
                for record in records:
                    all_events.append({
                        'timestamp': record.received_at.replace(tzinfo=timezone.utc) if record.received_at.tzinfo is None else record.received_at,
                        'user_idx': user_idx,
                        'grid_state': record.grid_state
                    })

        if not all_events:
            initial_state = any(last and last.grid_state for last in last_before_by_user if last)
            duration_seconds = (end_date - start_date).total_seconds()

            return PowerLogsResponse(
                periods = [PeriodResponse(
                    start_time       = start_date.isoformat(),
                    end_time         = end_date.isoformat(),
                    is_available     = initial_state,
                    duration_seconds = int(duration_seconds)
                )],
                total_available_seconds   = int(duration_seconds) if initial_state else 0,
                total_unavailable_seconds = int(duration_seconds) if not initial_state else 0,
                total_generator_seconds   = int(total_generator_seconds),
                total_seconds             = int(duration_seconds)
            )

        all_events.sort(key=lambda e: e['timestamp'])

        reporter_states = [
            (last.grid_state if last else False) 
            for last in last_before_by_user
        ]

        if all_events[0]['timestamp'] > start_date:
            initial_aggregate_state = any(reporter_states)
            all_events.insert(0, {
                'timestamp': start_date,
                'user_idx': -1, 
                'grid_state': initial_aggregate_state,
                'is_synthetic': True
            })

        periods = []
        total_available_seconds = 0
        total_unavailable_seconds = 0

        current_time = start_date
        current_aggregate_state = any(reporter_states)  # OR logic (pessimistic strategy)

        for event in all_events:
            event_time = event['timestamp']

            if event['user_idx'] >= 0:
                reporter_states[event['user_idx']] = event['grid_state']

            new_aggregate_state = any(reporter_states)

            if new_aggregate_state != current_aggregate_state or event_time == start_date:
                if event_time > current_time:
                    duration_seconds = (event_time - current_time).total_seconds()

                    periods.append(PeriodResponse(
                        start_time       = current_time.isoformat(),
                        end_time         = event_time.isoformat(),
                        is_available     = current_aggregate_state,
                        duration_seconds = int(duration_seconds)
                    ))

                    if current_aggregate_state:
                        total_available_seconds += duration_seconds
                    else:
                        total_unavailable_seconds += duration_seconds

                current_time = event_time
                current_aggregate_state = new_aggregate_state

        if current_time < end_date:
            duration_seconds = (end_date - current_time).total_seconds()

            periods.append(PeriodResponse(
                start_time       = current_time.isoformat(),
                end_time         = end_date.isoformat(),
                is_available     = current_aggregate_state,
                duration_seconds = int(duration_seconds)
            ))

            if current_aggregate_state:
                total_available_seconds += duration_seconds
            else:
                total_unavailable_seconds += duration_seconds

        total_seconds = int(total_available_seconds + total_unavailable_seconds)

        return PowerLogsResponse(
            periods                   = periods,
            total_available_seconds   = int(total_available_seconds),
            total_unavailable_seconds = int(total_unavailable_seconds),
            total_generator_seconds   = int(total_generator_seconds),
            total_seconds             = total_seconds,
        )
