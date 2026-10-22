import logging
from datetime import datetime, timezone

from injector import inject

from shared.language import DEFAULT_LANGUAGE
from shared.models.assumed_station_status import AssumedStationStatus
from shared.models.building import Building
from shared.models.station import Station
from app.repositories import IDashboardRepository, IPushTriggerStatesRepository, IStationsDataRepository
from ..dispatcher import PushEventDispatcher
from ..events import HYSTERESIS, THRESHOLD, PushEvent
from ..templates import PushTemplatesService, localize
from ..topics import BATTERY_LOW


logger = logging.getLogger(__name__)


@inject
class BatteryPushTriggers:
    """Low battery once per episode: fires at SoC <= threshold, re-arms above threshold + hysteresis."""
    def __init__(
        self,
        dispatcher: PushEventDispatcher,
        templates: PushTemplatesService,
        dashboard: IDashboardRepository,
        stations_data: IStationsDataRepository,
        states: IPushTriggerStatesRepository,
    ):
        self._dispatcher = dispatcher
        self._templates = templates
        self._dashboard = dashboard
        self._stations_data = stations_data
        self._states = states


    async def check(self):
        threshold = await self._templates.get_param_value(BATTERY_LOW, THRESHOLD)
        hysteresis = await self._templates.get_param_value(BATTERY_LOW, HYSTERESIS)

        # Stations not linked to a building are never checked
        checked = set()
        for building in await self._dashboard.get_buildings():
            station = building.station
            if not station or station.id in checked:
                continue
            checked.add(station.id)
            try:
                await self._check_station(building, station, threshold, hysteresis)
            except Exception as e:
                logger.error(f"Battery push check failed for station {station.id}: {e!r}")


    async def _is_offline(self, station: Station) -> bool:
        if station.connection_status == "ALL_OFFLINE":
            return True
        return await self._stations_data.get_assumed_connection_status(station.id) == AssumedStationStatus.OFFLINE


    async def _check_station(self, building: Building, station: Station, threshold: int, hysteresis: int):
        if not station.enabled or await self._is_offline(station):
            # Stale data says nothing about the battery now
            return
        data = await self._stations_data.get_last_station_data(station.id)
        if not data or data.battery_soc is None:
            return
        soc = data.battery_soc

        key = f"battery:{station.id}"
        state = await self._states.get_state(key) or { "armed": True }

        if state.get("armed", True):
            if soc > threshold:
                return
            reported_at = data.last_update_time or datetime.now(timezone.utc)
            if reported_at.tzinfo is None:
                reported_at = reported_at.replace(tzinfo=timezone.utc)
            episode = reported_at.isoformat()
            await self._states.set_state(key, { "armed": False, "episode": episode })
            await self._dispatcher.dispatch(self._event(building, station, soc, threshold, episode))
        elif soc > threshold + hysteresis:
            await self._states.set_state(key, { "armed": True })


    def _event(self, building: Building, station: Station, soc: float, threshold: int, episode: str) -> PushEvent:
        station_name = station.station_alias or station.station_name or str(station.station_id)
        return PushEvent(
            topic       = BATTERY_LOW,
            dedup_key   = f"battery:{station.id}:{episode}",
            context     = {
                "building": { "id": str(building.id), "name": building.name },
                "station": { "id": str(station.id), "name": station_name },
                "soc": round(soc),
                "threshold": threshold,
            },
            data        = { "buildingId": str(building.id), "stationId": str(station.id) },
            summary     = { "building": localize(building.name, DEFAULT_LANGUAGE), "soc": str(round(soc)) },
            building_id = building.id,
        )
