from contextlib import asynccontextmanager
from fastapi import FastAPI


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    import logging
    logging.info("Starting app-back-end...")
    yield
    # Shutdown
    import logging
    logging.info("Shutting down app-back-end...")