import logging
import sys
from uvicorn.logging import DefaultFormatter
from fastapi import FastAPI

from app.lifespan import create_app
from app.settings import settings
from app.routes import register_routes


handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(DefaultFormatter("%(levelprefix)s %(message)s", use_colors=True))

logging.basicConfig(
    level=logging.INFO,
    handlers=[handler]
)

app = create_app()
register_routes(app)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )