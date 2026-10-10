from contextlib import asynccontextmanager
from fastapi import FastAPI


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    import logging
    logging.info("Starting app-back-end...")
    
    # Initialize beanie
    from app.container import BeanieInitializer
    beanie_initializer = app.state.injector.get(BeanieInitializer)
    await beanie_initializer.init()
    
    yield
    # Shutdown
    import logging
    logging.info("Shutting down app-back-end...")