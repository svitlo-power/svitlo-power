from datetime import datetime
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from injector import Injector

from app.settings import Settings
from shared.models.dashboard_config import DashboardConfig
from shared.services import OutagesScheduleService

logger = logging.getLogger(__name__)


def register(_: Settings, injector: Injector):
    scheduler = injector.get(AsyncIOScheduler)

    async def update_outages_schedule():
        service = injector.get(OutagesScheduleService)
        config = await DashboardConfig.find_one()
        schedule = config.outages_schedule if config else None
        if not schedule or not schedule.enable or not schedule.region or not schedule.dso:
            return

        regions = await service.fetch_regions()
        region = next((item for item in regions if item["value"] == schedule.region), None)
        if region is None and schedule.region == "Kyiv":
            region = next((item for item in regions if item["id"] == 25), None)
        if region is None:
            logger.warning("Configured outage region %s is no longer available", schedule.region)
            return
        provider = next(
            (item for item in region["dsos"] if item["name"] == schedule.dso),
            None,
        )
        if provider is None and schedule.dso == "Yasno" and region["id"] == 25:
            provider = next((item for item in region["dsos"] if item["id"] == 902), None)
        if provider is None:
            logger.warning("Configured outage provider %s is unavailable in %s", schedule.dso, schedule.region)
            return
        await service.update(region["id"], provider["id"])

    scheduler.add_job(
        id            = 'update_outages_schedule',
        func          = update_outages_schedule,
        trigger       = 'interval',
        minutes       = 5,
        next_run_time = datetime.now(),
        max_instances = 1
    )
