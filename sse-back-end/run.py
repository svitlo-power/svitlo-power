# -*- encoding: utf-8 -*-

import logging
from shared.utils import get_version

from app.settings import get_settings, Settings
from app.main import create_app
from fastapi import FastAPI
import uvicorn

# Get version at module load time
VERSION = get_version()

settings: Settings = get_settings()

app: FastAPI = create_app(settings)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    logger.info(f"Starting svitlo-power-sse-back-end version {VERSION}")
    uvicorn.run(
        "run:app",
        host="0.0.0.0",
        port=5005,
        reload=settings.DEBUG
    )