import logging
import sys
from uvicorn.logging import DefaultFormatter
from fastapi import FastAPI
from fastapi_injector import InjectorMiddleware, attach_injector
from injector import Injector

from app.container import AppModule
from app.settings import get_settings, Settings
from app.routes import register_routes
from app.lifespan import lifespan


handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(DefaultFormatter("%(levelprefix)s %(message)s", use_colors=True))

logging.basicConfig(
    level=logging.INFO,
    handlers=[handler]
)


def create_app(settings: Settings) -> FastAPI:
    injector = Injector([AppModule()])
    app = FastAPI(
        title="SvitloPower App Backend",
        version="1.0.0",
        debug=settings.DEBUG,
        lifespan=lifespan
    )
    app.add_middleware(InjectorMiddleware, injector=injector)
    attach_injector(app, injector)
    app.state.settings = settings
    register_routes(app)
    return app


settings: Settings = get_settings()
app: FastAPI = create_app(settings)