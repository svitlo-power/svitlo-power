from injector import Injector
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.services import IExtDeviceService
from app.settings import Settings


def register(settings: Settings, injector: Injector):
    scheduler = injector.get(AsyncIOScheduler)

    async def check_pings():
        service = injector.get(IExtDeviceService)
        await service.check_pings()

    scheduler.add_job(
        id      = 'ping_check',
        func    = check_pings,
        trigger = 'interval',
        seconds = 30,
    )
