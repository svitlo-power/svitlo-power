import asyncio
import logging
from datetime import datetime, timezone

from injector import inject

from shared.language import DEFAULT_LANGUAGE
from shared.models.building import Building
from app.repositories import IDashboardRepository, IExtDataRepository, IPushTriggerStatesRepository
from ..dispatcher import PushEventDispatcher
from ..events import DEBOUNCE_SECONDS, PushEvent
from ..templates import PushTemplatesService, localize
from ..topics import POWER_STATUS


logger = logging.getLogger(__name__)


def _utc(value: datetime) -> datetime:
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


@inject
class PowerPushTriggers:
    """Power lost / restored per building, confirmed only after the state held for the debounce time.

    The building state is derived as on the dashboard: power is on while any report user reports it.
    A ping device that stops pinging reports the power as off, which counts as a power loss.
    """
    def __init__(
        self,
        dispatcher: PushEventDispatcher,
        templates: PushTemplatesService,
        dashboard: IDashboardRepository,
        ext_data: IExtDataRepository,
        states: IPushTriggerStatesRepository,
    ):
        self._dispatcher = dispatcher
        self._templates = templates
        self._dashboard = dashboard
        self._ext_data = ext_data
        self._states = states


    async def check(self, now: datetime | None = None):
        now = now or datetime.now(timezone.utc)
        debounce = await self._templates.get_param_value(POWER_STATUS, DEBOUNCE_SECONDS)
        for building in await self._dashboard.get_buildings():
            try:
                await self._check_building(building, debounce, now)
            except Exception as e:
                logger.error(f"Power push check failed for building {building.id}: {e!r}")


    async def _get_state(self, building: Building) -> tuple[bool, datetime] | None:
        """Current power state of the building and when the last report arrived."""
        reports = await asyncio.gather(
            *(self._ext_data.get_last_ext_data_by_user_id(user.id) for user in building.report_users)
        )
        reports = [r for r in reports if r]
        if not reports:
            return None
        available = any(r.grid_state for r in reports)
        return available, max(_utc(r.received_at) for r in reports)


    async def _check_building(self, building: Building, debounce: int, now: datetime):
        if not building.report_users:
            return
        current = await self._get_state(building)
        if current is None:
            return
        available, reported_at = current

        key = f"power:{building.id}"
        state = await self._states.get_state(key)
        if state is None:
            # First observation becomes the baseline, nothing changed yet
            await self._states.set_state(key, { "confirmed": available })
            return

        if available == state.get("confirmed"):
            if "pending" in state:
                # Flapped back within the debounce time
                await self._states.set_state(key, { "confirmed": available })
            return

        if state.get("pending") != available:
            state = { "confirmed": state.get("confirmed"), "pending": available, "since": reported_at.isoformat() }
            await self._states.set_state(key, state)

        since = datetime.fromisoformat(state["since"])
        if (now - since).total_seconds() < debounce:
            return

        await self._states.set_state(key, { "confirmed": available })
        await self._dispatcher.dispatch(self._event(building, available, since))


    def _event(self, building: Building, available: bool, changed_at: datetime) -> PushEvent:
        state = "on" if available else "off"
        return PushEvent(
            topic       = POWER_STATUS,
            dedup_key   = f"power:{building.id}:{state}:{changed_at.isoformat()}",
            context     = {
                "building": { "id": str(building.id), "name": building.name },
                "available": available,
                "changed_at": changed_at.astimezone(self._templates.timezone),
            },
            data        = { "buildingId": str(building.id) },
            summary     = { "building": localize(building.name, DEFAULT_LANGUAGE), "state": state },
            building_id = building.id,
        )
