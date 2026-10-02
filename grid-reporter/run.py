import asyncio
import logging
from shared.utils import get_version

from app.main import run

# Get version at module load time
VERSION = get_version()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    logger.info(f"Starting svitlo-power-grid-reporter version {VERSION}")
    try:
        asyncio.run(run())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Application terminated gracefully")
        raise SystemExit(0)