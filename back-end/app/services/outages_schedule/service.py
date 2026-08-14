import logging
import asyncio
from injector import inject
from pydantic import ValidationError
from datetime import datetime, timezone
import aiohttp

from app.services.base import BaseService
from shared.services.events.service import EventsService
from .models import SchedulesResponse, DayStatus


logger = logging.getLogger(__name__)


@inject
class OutagesScheduleService(BaseService):
    def __init__(self, events: EventsService, session: aiohttp.ClientSession):
        super().__init__(events)
        self._session = session
        self._cache = SchedulesResponse({})

    def get_schedule(self, queue: str):
        return self._cache.root.get(queue)

    async def update(self, region: int, dso: int):
        yasno_url = (
            f"https://app.yasno.ua/api/blackout-service/public/shutdowns/"
            f"regions/{region}/dsos/{dso}/planned-outages"
        )

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko)"
            ),
            "Accept": "application/json",
        }

        try:
            async with self._session.get(yasno_url, headers=headers, timeout=10) as resp:
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

            self._cache = parsed
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
