from contextlib import asynccontextmanager
from fastapi import FastAPI
from shared.services.settings.service import SettingsService
from shared.utils.power_estimation import set_settings_service


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

    yield

    # Shutdown - close resources in reverse order
    import logging
    logging.info("Shutting down app-back-end...")

    # Close aiohttp session
    if hasattr(app.state, 'aiohttp_session') and app.state.aiohttp_session:
        await app.state.aiohttp_session.close()

    # Close redis client
    if hasattr(app.state, 'redis_client') and app.state.redis_client:
        await app.state.redis_client.close()

    # Close mongo client
    if hasattr(app.state, 'mongo_client') and app.state.mongo_client:
        await app.state.mongo_client.close()
