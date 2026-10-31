from contextlib import asynccontextmanager
import logging
import sys
from uvicorn.logging import DefaultFormatter
from fastapi import FastAPI
from prometheus_client import ProcessCollector, REGISTRY
from app.settings import Settings
from app.routes import register_routes
from app.container import create_injector, set_injector
from shared.services import EventsService
from shared.services.events.models import EventsServiceConfig
from shared.utils.signals import register_chained_signal_handlers
from shared.metrics import SERVICE_VERSION_INFO
from shared.metrics.server import metrics_server_lifespan
from shared.utils import get_version

handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(DefaultFormatter("%(levelprefix)s %(message)s", use_colors=True))

logging.basicConfig(
    level=logging.INFO,
    handlers=[handler]
)

# Register process metrics (CPU, RAM, FDs) - guard against duplicate registration
try:
    REGISTRY.register(ProcessCollector())
except ValueError:
    # Already registered (e.g., in tests or shared process)
    pass

async def make_shutdown_handler(events: EventsService):
    async def shutdown(signum: int):
        await events.request_shutdown()
    return shutdown

@asynccontextmanager
async def lifespan(app: FastAPI):
    events: EventsService = app.state.events
    await events.start()

    register_chained_signal_handlers(
        handler=await make_shutdown_handler(events)
    )

    # Start metrics server on port 9098
    async with metrics_server_lifespan(host="0.0.0.0", port=9098):
        yield

    await events.shutdown()

def create_app(settings: Settings = None):
    app = FastAPI(
        title = "SvitloPower SSE",
        version = "1.1.6",
        debug = settings.DEBUG,
        lifespan = lifespan,
    )

    # Create injector
    injector = create_injector(settings)
    set_injector(app, injector)

    config = EventsServiceConfig(str(settings.REDIS_URI), settings.DEBUG)
    events = EventsService(config)
    app.state.events = events
    register_routes(app, events, settings)

    # Register service version metric
    version = get_version()
    SERVICE_VERSION_INFO.labels(service="sse-back-end", version=version).set(1)

    # Set apscheduler loggers to WARNING level in production to reduce noise
    if not settings.DEBUG:
        logging.getLogger("apscheduler").setLevel(logging.WARNING)
        logging.getLogger("apscheduler.executors").setLevel(logging.WARNING)
        logging.getLogger("apscheduler.jobstores").setLevel(logging.WARNING)

    return app