import asyncio
import os
import signal
from fastapi import FastAPI
from injector import Injector
from contextlib import asynccontextmanager
from prometheus_client import ProcessCollector, REGISTRY

from app.app_container import bind_client_session, init_container
from app.settings import Settings
from app.jobs import register_jobs
from app.scheduler_metrics import register_scheduler_metrics
from app.routes import register_routes
from app.services import AuthorizationService, BeanieInitializer, BotsService, TelegramService, StationConnectionsService, PushService
from app.state import set_injector
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from shared.services.events.service import EventsService
from shared.services.settings.service import SettingsService
from shared.utils.power_estimation import set_settings_service
from shared.utils.signals import register_chained_signal_handlers
from shared.metrics.endpoint import add_metrics_endpoint

# Register process metrics (CPU, RAM, FDs) - guard against duplicate registration
try:
    REGISTRY.register(ProcessCollector())
except ValueError:
    # Already registered (e.g., in tests or shared process)
    pass


async def create_user(settings: Settings, injector: Injector):
    if settings.ADMIN_USER is not None:
        authorization = injector.get(AuthorizationService)
        await authorization.add_user(settings.ADMIN_USER, settings.ADMIN_PASSWORD)


async def setup_bots(injector: Injector):
    bots_service = injector.get(BotsService)
    telegram_service = injector.get(TelegramService)
    bots = await bots_service.get_enabled_bots()
    for bot in bots:
        await telegram_service.add_bot(bot.id, bot.token, bot.hook_enabled)


async def setup_push_topics(injector: Injector):
    await injector.get(PushService).ensure_default_topics()


async def setup_settings(injector: Injector):
    """Initialize settings service."""
    settings_service = injector.get(SettingsService)
    set_settings_service(settings_service)


async def make_shutdown_handler(events: EventsService):
    async def shutdown(signum: int):
        await events.request_shutdown()
    return shutdown


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings: Settings = app.state.settings
    injector = init_container(app, settings)
    app.state.injector = injector
    set_injector(app, injector)

    bind_client_session(injector)
    beanie_initializer = injector.get(BeanieInitializer)
    await beanie_initializer.init()

    deye_connections = injector.get(StationConnectionsService)
    await deye_connections.init()

    telegram_service = injector.get(TelegramService)

    events: EventsService = injector.get(EventsService)
    await events.start()

    scheduler = injector.get(AsyncIOScheduler)
    register_jobs(settings, injector)
    register_scheduler_metrics(scheduler)
    scheduler.start()

    register_routes(app)
    add_metrics_endpoint(app)

    await setup_bots(injector)
    await create_user(settings, injector)
    await setup_push_topics(injector)
    await setup_settings(injector)

    register_chained_signal_handlers(
        handler=await make_shutdown_handler(events)
    )

    yield

    try:
        scheduler.shutdown(wait=False)
    except Exception:
        pass

    await events.shutdown()
    await telegram_service.shutdown()
    await deye_connections.shutdown()