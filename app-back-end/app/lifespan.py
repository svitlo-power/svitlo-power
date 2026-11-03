from contextlib import asynccontextmanager
from fastapi import FastAPI
from prometheus_client import ProcessCollector, REGISTRY
from shared.services.settings.service import SettingsService
from shared.utils.power_estimation import set_settings_service
from shared.metrics import SERVICE_VERSION_INFO
from shared.metrics.server import metrics_server_lifespan
from shared.utils import get_version
from shared.clients.dashboard_snapshot_client import DashboardSnapshotClient
from app.middleware.shadow_compare import ShadowCompareMiddleware

# Register process metrics (CPU, RAM, FDs) - guard against duplicate registration
try:
    REGISTRY.register(ProcessCollector())
except ValueError:
    # Already registered (e.g., in tests or shared process)
    pass


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    import logging
    logging.info("Starting app-back-end...")

    # Initialize beanie
    from app.container import BeanieInitializer
    beanie_initializer = app.state.injector.get(BeanieInitializer)
    await beanie_initializer.init()

    # Get resources that need cleanup
    import aiohttp
    import redis.asyncio as redis

    # Store resources in app.state for cleanup
    app.state.mongo_client = beanie_initializer._client
    app.state.aiohttp_session = app.state.injector.get(aiohttp.ClientSession)
    app.state.redis_client = app.state.injector.get(redis.Redis)

    settings_service = app.state.injector.get(SettingsService)
    set_settings_service(settings_service)

    # Register service version metric
    version = get_version()
    SERVICE_VERSION_INFO.labels(service="app-back-end", version=version).set(1)

    # Start dashboard snapshot client (Phase 2)
    snapshot_client = app.state.injector.get(DashboardSnapshotClient)
    app.state.snapshot_client = snapshot_client
    await snapshot_client.start()

    # Start shadow comparison middleware (Phase 2)
    shadow_compare = app.state.injector.get(ShadowCompareMiddleware)
    app.state.shadow_compare = shadow_compare
    await shadow_compare.start()

    # Start metrics server on port 9097
    async with metrics_server_lifespan(host="0.0.0.0", port=9097):
        yield

    # Shutdown - close resources in reverse order
    import logging
    logging.info("Shutting down app-back-end...")

    # Stop shadow comparison
    if hasattr(app.state, 'shadow_compare') and app.state.shadow_compare:
        await app.state.shadow_compare.stop()

    # Stop snapshot client
    if hasattr(app.state, 'snapshot_client') and app.state.snapshot_client:
        await app.state.snapshot_client.stop()

    # Close aiohttp session
    if hasattr(app.state, 'aiohttp_session') and app.state.aiohttp_session:
        await app.state.aiohttp_session.close()

    # Close redis client
    if hasattr(app.state, 'redis_client') and app.state.redis_client:
        await app.state.redis_client.close()

    # Close mongo client
    if hasattr(app.state, 'mongo_client') and app.state.mongo_client:
        await app.state.mongo_client.close()
