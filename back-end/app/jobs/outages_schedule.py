from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from injector import Injector

from app.settings import Settings
from shared.services import OutagesScheduleService


def register(_: Settings, injector: Injector):
    scheduler = injector.get(AsyncIOScheduler)

    async def update_outages_schedule():
        # TODO: fetch from config
        service = injector.get(OutagesScheduleService)
        await service.update(25, 902)

    scheduler.add_job(
        id            = 'update_outages_schedule',
        func          = update_outages_schedule,
        trigger       = 'interval',
        minutes       = 5,
        next_run_time = datetime.now(),
        max_instances = 1
    )
