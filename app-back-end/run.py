# -*- encoding: utf-8 -*-

import logging
from shared.utils import get_version

from app.settings import settings
from app.main import app
import uvicorn

# Get version at module load time
VERSION = get_version()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    logger.info(f"Starting svitlo-power-app-back-end version {VERSION}")
    uvicorn.run(
        "run:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        timeout_graceful_shutdown=5,
    )