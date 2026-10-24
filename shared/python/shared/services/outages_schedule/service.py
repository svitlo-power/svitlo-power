import logging
import asyncio
from injector import inject
from pydantic import ValidationError
from datetime import datetime, timezone
import aiohttp

from shared.services.events.service import EventsService
from shared.repositories.interfaces.outages_schedule import IOutagesScheduleRepository
from .models import SchedulesResponse, DayStatus


logger = logging.getLogger(__name__)


class BaseService:
    """Base service class for shared services."""
    def __init__(self, events: EventsService):
        self._events = events

    async def broadcast_public(self, type: str, data: dict = None):
        await self._events.broadcast_public(type, data)

    async def broadcast_private(self, type: str, data: dict = None):
        await self._events.broadcast_private(type, data)


@inject
class OutagesScheduleService(BaseService):
    YASNO_API = "https://app.yasno.ua/api/blackout-service/public/shutdowns"
    YASNO_REGIONS_API = (
        "https://app.yasno.ua/api/blackout-service/public/shutdowns/"
        "addresses/v2/regions"
    )

    def __init__(
        self, 
        events: EventsService, 
        session: aiohttp.ClientSession,
        repository: IOutagesScheduleRepository
    ):
        super().__init__(events)
        self._session = session
        self._repository = repository
        self._regions = None

    async def _fetch_yasno_json(self, url: str):
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko)"
            ),
            "Accept": "application/json",
        }
        async with self._session.get(url, headers=headers, timeout=10) as response:
            response.raise_for_status()
            return await response.json()

    async def fetch_regions(self):
        """Fetch and cache regions and their providers from YASNO."""
        data = await self._fetch_yasno_json(self.YASNO_REGIONS_API)
        if isinstance(data, dict):
            data = data.get("regions", data.get("items", []))
        if not isinstance(data, list):
            raise ValueError("Unexpected regions response from YASNO")

        regions = []
        for item in data:
            if not isinstance(item, dict):
                continue
            name = item.get("value") or item.get("name") or item.get("regionName")
            region_id = item.get("id") or item.get("regionId")
            if name is None or region_id is None:
                continue
            providers = item.get("dsos") or item.get("providers") or []
            regions.append({
                "id": int(region_id),
                "value": str(name),
                "label": str(name),
                "dsos": [
                    {
                        "id": int(provider.get("id") or provider.get("dsoId")),
                        "name": str(provider.get("name") or provider.get("value")),
                    }
                    for provider in providers
                    if isinstance(provider, dict)
                    and (provider.get("id") or provider.get("dsoId")) is not None
                    and (provider.get("name") or provider.get("value")) is not None
                ],
            })

        self._regions = regions
        return regions

    def get_providers_for_region(self, region_name: str):
        """Return providers for a region from the most recently fetched region list."""
        if self._regions is None:
            raise RuntimeError("Regions have not been fetched")
        region = next(
            (item for item in self._regions if item["value"] == region_name),
            None,
        )
        if region is None:
            raise KeyError(f"Unknown YASNO region: {region_name}")
        return region["dsos"]

    async def fetch_providers_for_region(self, region_name: str):
        if self._regions is None:
            await self.fetch_regions()
        return self.get_providers_for_region(region_name)

    async def fetch_queues(self, region_id: int, dso_id: int):
        """Fetch available queue names for a region and provider."""
        url = f"{self.YASNO_API}/regions/{region_id}/dsos/{dso_id}/planned-outages"
        data = await self._fetch_yasno_json(url)
        if isinstance(data, dict):
            return list(data.keys())
        if isinstance(data, list):
            return [
                str(item.get("name") or item.get("value"))
                for item in data
                if isinstance(item, dict) and (item.get("name") or item.get("value"))
            ]
        raise ValueError("Unexpected queues response from YASNO")

    def get_schedule(self, queue: str):
        # This is a synchronous method for backward compatibility
        # We'll need to handle this differently - maybe cache locally
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If we're in an async context, we can't block
                # Return cached data or None
                return None
            else:
                return loop.run_until_complete(self._repository.get_schedule(queue))
        except RuntimeError:
            # No event loop
            return None

    async def get_schedule_async(self, queue: str):
        """Async version of get_schedule."""
        return await self._repository.get_schedule(queue)

    async def update(self, region: int, dso: int):
        yasno_url = f"{self.YASNO_API}/regions/{region}/dsos/{dso}/planned-outages"

        try:
            async with self._session.get(
                yasno_url,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko)"
                    ),
                    "Accept": "application/json",
                },
                timeout=10,
            ) as resp:
                if resp.status != 200:
                    logger.warning(f"Failed to fetch YASNO data. Status: {resp.status}")
                    return None

                data = await resp.json()

            transformed_data = {}
            for queue, unit_data in data.items():
                days_list = []
                if "today" in unit_data:
                    days_list.append(unit_data["today"])
                if "tomorrow" in unit_data:
                    days_list.append(unit_data["tomorrow"])
                transformed_data[queue] = {
                    "days": days_list,
                    "updatedOn": unit_data.get("updatedOn")
                }

            parsed = SchedulesResponse.model_validate(transformed_data)

            now = datetime.now(timezone.utc)
            for unit in parsed.root.values():
                for day in unit.days:
                    day_date = (
                        day.date.replace(tzinfo=timezone.utc)
                        if day.date.tzinfo is None 
                        else day.date.astimezone(timezone.utc)
                    )
                    if abs((day_date.date() - now.date()).days) > 2:
                        day.status = DayStatus.WaitingForSchedule

            await self._repository.set_schedule(parsed)
            await self.broadcast_public("outages_updated")

        except aiohttp.ClientConnectionError as e:
            logger.error(f"YASNO connection error: {e}")
            return None

        except asyncio.TimeoutError:
            logger.error("Timeout while requesting YASNO API")
            return None

        except aiohttp.ClientError as e:
            logger.error(f"YASNO request error: {e}")
            return None

        except ValidationError as ve:
            logger.error(f"Validation error: {ve}")
            return None

        except Exception as e:
            logger.error(f"Internal error in outage schedule update: {e}")
            return None