from datetime import datetime
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from injector import Injector

from app.settings import Settings
from shared.services import OutagesScheduleService
from shared.services.dashboard.config_settings import (
    DASHBOARD_OUTAGES_SCHEDULE_ENABLED_SETTING_KEY,
    DASHBOARD_OUTAGES_SCHEDULE_REGION_SETTING_KEY,
    DASHBOARD_OUTAGES_SCHEDULE_DSO_SETTING_KEY,
)
from shared.services.settings.service import SettingsService

logger = logging.getLogger(__name__)


def register(_: Settings, injector: Injector):
    scheduler = injector.get(AsyncIOScheduler)

    async def update_outages_schedule():
        service = injector.get(OutagesScheduleService)
        settings = injector.get(SettingsService)
        enabled = await settings.get_boolean(
            DASHBOARD_OUTAGES_SCHEDULE_ENABLED_SETTING_KEY,
            False,
        )
        if not enabled:
            return

        region_name = await settings.get_text(DASHBOARD_OUTAGES_SCHEDULE_REGION_SETTING_KEY)
        dso_name = await settings.get_text(DASHBOARD_OUTAGES_SCHEDULE_DSO_SETTING_KEY)
        if not region_name or not dso_name:
            logger.warning("Outage schedule is enabled without a configured region and provider")
            return

        regions = await service.fetch_regions()
        region = next((item for item in regions if item["value"] == region_name), None)
        if region is None and region_name == "Kyiv":
            region = next((item for item in regions if item["id"] == 25), None)
        if region is None:
            logger.warning("Configured outage region %s is no longer available", region_name)
            return
        provider = next(
            (item for item in region["dsos"] if item["name"] == dso_name),
            None,
        )
        if provider is None and dso_name == "Yasno" and region["id"] == 25:
            provider = next((item for item in region["dsos"] if item["id"] == 902), None)
        if provider is None:
            logger.warning("Configured outage provider %s is unavailable in %s", dso_name, region_name)
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
