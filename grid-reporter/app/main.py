import asyncio
from contextlib import ExitStack
import logging
import signal
import platform
import sys
from typing import Any

import aiohttp
from aiohttp import ClientTimeout
from prometheus_client import ProcessCollector, REGISTRY

from shared.services.deye_api import BaseDeyeClient
from shared.health import health_registry, HealthCheckResult, HealthStatus

# Register process metrics (CPU, RAM, FDs) - guard against duplicate registration
try:
    REGISTRY.register(ProcessCollector())
except ValueError:
    # Already registered (e.g., in tests or shared process)
    pass

from .client_worker import ClientWorker
from .service import load_clients
from .settings import load_settings
from .state_store import StateStore
from .health_server import run_health_server


_shutdown_event: asyncio.Event | None = None

def _signal_handler(signum: int, frame: Any) -> None:
    if _shutdown_event:
        _shutdown_event.set()


def register_health_checks():
    """Register health checks for grid-reporter."""
    
    async def check_deye_clients():
        """Check Deye API clients."""
        try:
            settings = load_settings()
            clients = load_clients(settings.clients_path, settings)
            
            return HealthCheckResult(
                status=HealthStatus.HEALTHY,
                component="deye_clients",
                details={"clients_loaded": len(clients)},
            )
        except Exception as e:
            return HealthCheckResult(
                status=HealthStatus.UNHEALTHY,
                component="deye_clients",
                message=str(e),
            )
    
    async def check_state_store():
        """Check state store."""
        try:
            settings = load_settings()
            state_store = StateStore(settings.state_path)
            return HealthCheckResult(
                status=HealthStatus.HEALTHY,
                component="state_store",
                details={"path": settings.state_path},
            )
        except Exception as e:
            return HealthCheckResult(
                status=HealthStatus.UNHEALTHY,
                component="state_store",
                message=str(e),
            )
    
    # Register all checks
    health_registry.register("deye_clients", check_deye_clients)
    health_registry.register("state_store", check_state_store)


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

    clients = load_clients(settings.clients_path, settings)
    if not clients:
        logging.error("No clients loaded; exiting")
        return

    timeout = ClientTimeout(total=settings.timeout)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        state_store = StateStore(settings.state_path)
        tasks = []

        for client in clients:
            deye_client = BaseDeyeClient(client.deye, session)
            worker = ClientWorker(client, deye_client, session, state_store, settings)
            tasks.append(asyncio.create_task(worker.run()))

        # Start health check server
        health_task = asyncio.create_task(run_health_server(settings.health_port if hasattr(settings, 'health_port') else 8081))

        try:
            shutdown_task = asyncio.create_task(_shutdown_event.wait())

            done, pending = await asyncio.wait(
                tasks + [shutdown_task, health_task],
                return_when=asyncio.FIRST_COMPLETED,
            )

            if shutdown_task in done:
                logging.info("Shutdown signal received, cancelling all tasks...")
                for task in tasks:
                    task.cancel()
                health_task.cancel()

            await asyncio.gather(*tasks, health_task, return_exceptions=True)
            logging.info("All tasks cancelled")
        except asyncio.CancelledError:
            logging.info("Shutdown signal received, cancelling all tasks...")
            for task in tasks:
                task.cancel()
            health_task.cancel()
            await asyncio.gather(*tasks, health_task, return_exceptions=True)
            logging.info("All tasks cancelled")
            logging.shutdown()
            raise