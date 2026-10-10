import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi_injector import InjectorMiddleware, attach_injector
from injector import Injector

from app.container import AppModule
from app.settings import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logging.info("Starting app-back-end...")
    yield
    # Shutdown
    logging.info("Shutting down app-back-end...")


def create_app() -> FastAPI:
    injector = Injector([AppModule()])
    app = FastAPI(
        title="SvitloPower App Backend",
        version="1.0.0",
        debug=settings.DEBUG,
        lifespan=lifespan,
    )
    app.add_middleware(InjectorMiddleware, injector=injector)
    attach_injector(app, injector)
    app.state.settings = settings
    return app