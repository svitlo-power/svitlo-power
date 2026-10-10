import json
import redis.asyncio as redis
from typing import Optional

from shared.repositories.interfaces.outages_schedule import IOutagesScheduleRepository
from shared.services.outages_schedule.models import SchedulesResponse


class RedisOutagesScheduleRepository(IOutagesScheduleRepository):
    """Redis implementation of outages schedule repository."""

    REDIS_KEY = "outages_schedule"

    def __init__(self, redis_uri: str):
        self._redis = redis.from_url(redis_uri, decode_responses=True)

    async def get_schedule(self, queue: str) -> Optional[SchedulesResponse]:
        """Get schedule for a specific queue."""
        data = await self._redis.hget(self.REDIS_KEY, queue)
        if data is None:
            return None
        return SchedulesResponse.model_validate_json(data)

    async def set_schedule(self, schedule: SchedulesResponse) -> None:
        """Set the entire schedule data."""
        # Store each queue as a separate hash field for efficient partial updates
        mapping = {}
        for queue, unit_schedule in schedule.root.items():
            mapping[queue] = unit_schedule.model_dump_json()
        if mapping:
            await self._redis.hset(self.REDIS_KEY, mapping=mapping)

    async def get_all_schedules(self) -> SchedulesResponse:
        """Get all schedules."""
        data = await self._redis.hgetall(self.REDIS_KEY)
        if not data:
            return SchedulesResponse({})
        
        # Reconstruct the SchedulesResponse from hash fields
        root = {}
        for queue, unit_data in data.items():
            root[queue] = json.loads(unit_data)
        return SchedulesResponse(root)

    async def close(self):
        """Close the Redis connection."""
        await self._redis.close()