from injector import Injector
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.settings import Settings
from shared.services.events.service import EventsService
from shared.features import feature_flags, FeatureFlag


def register(settings: Settings, injector: Injector):
    scheduler = injector.get(AsyncIOScheduler)

    async def send_ping():
        # Only send ping if SSE Redis migration is enabled
        if feature_flags.is_enabled(FeatureFlag.BACKEND_SSE_REDIS):
            events = injector.get(EventsService)
            await events.broadcast_public("ping")

    if settings.SSE_PING_INTERVAL > 0:
        scheduler.add_job(
            id      = 'send_ping',
            func    = send_ping,
            trigger = 'interval',
            seconds = settings.SSE_PING_INTERVAL,
        )
