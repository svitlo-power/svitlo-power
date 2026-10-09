from abc import ABC, abstractmethod
from typing import Optional

from shared.services.outages_schedule.models import SchedulesResponse


class IOutagesScheduleRepository(ABC):
    """Interface for outages schedule data access."""

    @abstractmethod
    async def get_schedule(self, queue: str) -> Optional[SchedulesResponse]:
        """Get schedule for a specific queue."""
        pass

    @abstractmethod
    async def set_schedule(self, schedule: SchedulesResponse) -> None:
        """Set the entire schedule data."""
        pass

    @abstractmethod
    async def get_all_schedules(self) -> SchedulesResponse:
        """Get all schedules."""
        pass