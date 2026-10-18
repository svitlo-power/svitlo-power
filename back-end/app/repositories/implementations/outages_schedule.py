from typing import Optional

from shared.repositories.interfaces.outages_schedule import IOutagesScheduleRepository
from shared.services.outages_schedule.models import SchedulesResponse


class InMemoryOutagesScheduleRepository(IOutagesScheduleRepository):
    """In-memory implementation of outages schedule repository for local development."""

    def __init__(self):
        self._cache = SchedulesResponse({})

    async def get_schedule(self, queue: str) -> Optional[SchedulesResponse]:
        """Get schedule for a specific queue."""
        unit = self._cache.root.get(queue)
        if unit is None:
            return None
        return SchedulesResponse({queue: unit})

    async def set_schedule(self, schedule: SchedulesResponse) -> None:
        """Set the entire schedule data."""
        self._cache = schedule

    async def get_all_schedules(self) -> SchedulesResponse:
        """Get all schedules."""
        return self._cache