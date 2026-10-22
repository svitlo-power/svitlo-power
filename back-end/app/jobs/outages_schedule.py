import logging
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from injector import Injector

from app.settings import Settings
from app.services import SchedulePushTriggers
from shared.services import OutagesScheduleService


logger = logging.getLogger(__name__)


def register(settings: Settings, injector: Injector):
    scheduler = injector.get(AsyncIOScheduler)

    async def update_outages_schedule():
        service = injector.get(OutagesScheduleService)
        update = await service.update(settings.OUTAGES_REGION, settings.OUTAGES_DSO)
        if not update or not update.changed:
            return
        try:
            await injector.get(SchedulePushTriggers).on_schedule_updated(update)
        except Exception as e:
            # Notifications must not break the schedule update
            logger.error(f"Schedule push triggers failed: {e!r}")

    scheduler.add_job(
        id            = 'update_outages_schedule',
        func          = update_outages_schedule,
        trigger       = 'interval',
        minutes       = 5,
        next_run_time = datetime.now(),
        max_instances = 1
    )
