import logging
from injector import Injector
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.services import BatteryPushTriggers, PowerPushTriggers, SchedulePushTriggers
from app.settings import Settings


logger = logging.getLogger(__name__)


def register(settings: Settings, injector: Injector):
    scheduler = injector.get(AsyncIOScheduler)

    async def check_outage_upcoming():
        try:
            await injector.get(SchedulePushTriggers).check_upcoming()
        except Exception as e:
            logger.error(f"Outage reminder check failed: {e!r}")

    async def check_power_status():
        try:
            await injector.get(PowerPushTriggers).check()
        except Exception as e:
            logger.error(f"Power status check failed: {e!r}")

    async def check_battery_low():
        try:
            await injector.get(BatteryPushTriggers).check()
        except Exception as e:
            logger.error(f"Battery check failed: {e!r}")

    scheduler.add_job(
        id            = 'push_outage_upcoming',
        func          = check_outage_upcoming,
        trigger       = 'interval',
        seconds       = 60,
        max_instances = 1,
    )
    scheduler.add_job(
        id            = 'push_power_status',
        func          = check_power_status,
        trigger       = 'interval',
        seconds       = 15,
        max_instances = 1,
    )
    scheduler.add_job(
        id            = 'push_battery_low',
        func          = check_battery_low,
        trigger       = 'interval',
        seconds       = 60,
        max_instances = 1,
    )
