import asyncio
from contextlib import ExitStack
import logging
import signal
import platform
import sys
from typing import Any

from prometheus_client import ProcessCollector, REGISTRY
from shared.metrics.jobs import SERVICE_VERSION_INFO
from shared.utils.version import get_version


# Register process metrics (CPU, RAM, FDs) - guard against duplicate registration
try:
    REGISTRY.register(ProcessCollector())
except ValueError:
    # Already registered (e.g., in tests or shared process)
    pass

from .scheduler import create_scheduler, setup_scheduler_jobs, shutdown_scheduler
from .service import load_clients
from .settings import load_settings
from .health_checks import register_health_checks
from .health_server import run_health_server


_shutdown_event: asyncio.Event | None = None

def _signal_handler(signum: int, frame: Any) -> None:
    if _shutdown_event:
        _shutdown_event.set()


async def run() -> ExitStack:
    global _shutdown_event
    _shutdown_event = asyncio.Event()

    loop = asyncio.get_event_loop()
    if platform.system().lower() != "windows":
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, _signal_handler, sig, None)

    settings = load_settings()

    logging.basicConfig(
        level=settings.log_level,
        format="%(asctime)s %(levelname)s %(message)s",
        stream=sys.stdout,
        force=True,
    )
    logging.getLogger().handlers[0].setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    )
    logging.getLogger().handlers[0].flush()

    # Register health checks
    register_health_checks()

    # Create scheduler and jobs
    scheduler = create_scheduler()
    workers = setup_scheduler_jobs(scheduler, settings)
    if not workers:
        logging.error("No workers created; exiting")
        return
    
    scheduler.start()
    logging.info("Scheduler started with %d jobs", len(scheduler.get_jobs()))

    # Register service version metric
    version = get_version()
    SERVICE_VERSION_INFO.labels(service="grid-reporter", version=version).set(1)

    # Start health check server in background
    health_task = asyncio.create_task(run_health_server(settings.health_port if hasattr(settings, 'health_port') else 8081))

    try:
        # Wait only for shutdown signal
        await _shutdown_event.wait()
        logging.info("Shutdown signal received, cancelling all tasks...")
        health_task.cancel()
        await shutdown_scheduler(scheduler, workers)
        await asyncio.gather(health_task, return_exceptions=True)
        logging.info("All tasks cancelled")
    except asyncio.CancelledError:
        logging.info("Shutdown signal received, cancelling all tasks...")
        health_task.cancel()
        await shutdown_scheduler(scheduler, workers)
        await asyncio.gather(health_task, return_exceptions=True)
        logging.info("All tasks cancelled")
        logging.shutdown()
        raise