import logging
import sys
from uvicorn.logging import DefaultFormatter
from fastapi import Depends, FastAPI
from fastapi_injector import InjectorMiddleware, attach_injector
from injector import Injector

from app.container import AppModule
from app.settings import Settings
from app.routes import register_routes
from app.lifespan import lifespan
from app.auth import verify_app_token


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
        lifespan=lifespan,
        docs_url="/docs" if settings.DEBUG else None,
        redoc_url="/redoc" if settings.DEBUG else None,
        openapi_url="/openapi.json" if settings.DEBUG else None,
        dependencies=[Depends(verify_app_token)],
    )
    app.add_middleware(InjectorMiddleware, injector=injector)
    attach_injector(app, injector)
    app.state.settings = settings
    app.state.injector = injector
    if not settings.APP_ACCESS_TOKEN:
        logging.warning("APP_ACCESS_TOKEN is not set, app token check is disabled")
    register_routes(app)
    return app
