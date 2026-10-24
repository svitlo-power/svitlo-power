import asyncio
import logging

import aiohttp
from fastapi import FastAPI, HTTPException, Path
from fastapi_injector import Injected
from shared.services import OutagesScheduleService

logger = logging.getLogger(__name__)


def register(app: FastAPI):
    @app.get("/api/outagesSchedule/regions")
    async def get_outage_regions(
        outages_schedule = Injected(OutagesScheduleService),
    ):
        try:
            return await outages_schedule.fetch_regions()
        except aiohttp.ClientResponseError as error:
            logger.warning("YASNO regions request failed: %s", error)
            raise HTTPException(
                status_code=404 if error.status == 404 else 502,
                detail="Unable to fetch YASNO regions",
            ) from error
        except (aiohttp.ClientError, asyncio.TimeoutError, ValueError) as error:
            logger.warning("YASNO regions request failed: %s", error)
            raise HTTPException(status_code=502, detail="Unable to fetch YASNO regions") from error

    @app.get("/api/outagesSchedule/providers/{region_name}")
    async def get_outage_providers(
        region_name: str = Path(..., description="YASNO region name"),
        outages_schedule = Injected(OutagesScheduleService),
    ):
        try:
            return await outages_schedule.fetch_providers_for_region(region_name)
        except KeyError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except aiohttp.ClientResponseError as error:
            logger.warning("YASNO providers request failed: %s", error)
            raise HTTPException(
                status_code=404 if error.status == 404 else 502,
                detail="Unable to fetch YASNO providers",
            ) from error
        except (aiohttp.ClientError, asyncio.TimeoutError, ValueError) as error:
            logger.warning("YASNO providers request failed: %s", error)
            raise HTTPException(status_code=502, detail="Unable to fetch YASNO providers") from error

    @app.get("/api/outagesSchedule/queues/{region_id}/{dso_id}")
    async def get_outage_queues(
        region_id: int,
        dso_id: int,
        outages_schedule = Injected(OutagesScheduleService),
    ):
        try:
            return await outages_schedule.fetch_queues(region_id, dso_id)
        except aiohttp.ClientResponseError as error:
            logger.warning("YASNO queues request failed: %s", error)
            raise HTTPException(
                status_code=404 if error.status == 404 else 502,
                detail="Unable to fetch YASNO queues",
            ) from error
        except (aiohttp.ClientError, asyncio.TimeoutError, ValueError) as error:
            logger.warning("YASNO queues request failed: %s", error)
            raise HTTPException(status_code=502, detail="Unable to fetch YASNO queues") from error

    @app.get("/api/outagesSchedule/outagesSchedule/{queue}")
    async def get_outages_schedule(
        queue: str = Path(..., description="Queue name"),
        outages_schedule = Injected(OutagesScheduleService),    
    ):
        sched = await outages_schedule.get_schedule_async(queue)
        if sched is None or queue not in sched.root:
            raise HTTPException(status_code=404, detail=f"No schedule found for queue {queue}")
        # Return unwrapped UnitSchedule data (days array) as expected by front-end
        return sched.root[queue].model_dump()
