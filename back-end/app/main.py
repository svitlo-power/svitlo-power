
import logging
import sys
from uvicorn.logging import DefaultFormatter
from fastapi import FastAPI

from app.settings import Settings
from app.middlewares import LanguageMiddleware
from .lifespan import lifespan


handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(DefaultFormatter("%(levelprefix)s %(message)s", use_colors=True))

logging.basicConfig(
    level=logging.INFO,
    handlers=[handler]
)


def create_app(settings: Settings) -> FastAPI:
    app = FastAPI(
        title="SvitloPower",
        version="1.1.6",
        debug=settings.DEBUG,
        lifespan=lifespan
    )

    app.add_middleware(LanguageMiddleware)
    app.state.settings = settings

    # Set apscheduler loggers to WARNING level in production to reduce noise
    if not settings.DEBUG:
        logging.getLogger("apscheduler").setLevel(logging.WARNING)
        logging.getLogger("apscheduler.executors").setLevel(logging.WARNING)
        logging.getLogger("apscheduler.jobstores").setLevel(logging.WARNING)

    return app
