from injector import Injector
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.services import MaintenanceService
from app.settings import Settings
from shared.features import feature_flags, FeatureFlag


def register(settings: Settings, injector: Injector):
    scheduler = injector.get(AsyncIOScheduler)

    async def delete_old_data():
        # Only run cleanup if migration is enabled
        if feature_flags.is_enabled(FeatureFlag.CLEANUP_PROCESSING):
            service = injector.get(MaintenanceService)
            await service.delete_old_data(settings.STATISTIC_KEEP_DAYS)

    scheduler.add_job(
        id      = 'delete_old_data',
        func    = delete_old_data,
        trigger = 'cron',
        hour    = '0',
        minute  = '10',
        second  = '0',
    )
