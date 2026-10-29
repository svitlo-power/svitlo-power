"""APScheduler setup and job management for grid-reporter."""
import asyncio
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.memory import MemoryJobStore

from .client_worker import ClientWorker
from .service import load_clients
from .settings import Settings
from .scheduler_metrics import register_scheduler_metrics

logger = logging.getLogger(__name__)


def create_scheduler() -> AsyncIOScheduler:
    """Create and configure APScheduler."""
    jobstores = {
        "default": MemoryJobStore(),
    }
    scheduler = AsyncIOScheduler(
        jobstores=jobstores,
        timezone="UTC",
    )
    # Register scheduler metrics (same as back-end)
    register_scheduler_metrics(scheduler)
    return scheduler


def create_client_job(
    scheduler: AsyncIOScheduler,
    client_worker: ClientWorker,
    poll_interval: int,
    client_id: str,
) -> None:
    """Create a scheduled job for a client worker."""
    job_id = f"client_poll_{client_id}"

    # Remove existing job if present
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)

    async def job_wrapper():
        """Wrapper to execute client worker poll."""
        try:
            await client_worker.poll_and_sync()
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.exception("Job failed for client %s: %s", client_id, e)
            raise

    scheduler.add_job(
        job_wrapper,
        id=job_id,
        trigger="interval",
        seconds=poll_interval,
        max_instances=1,
        coalesce=True,
        misfire_grace_time=30,
    )

    logger.info("Created job %s with interval %ss", job_id, poll_interval)


def setup_scheduler_jobs(scheduler: AsyncIOScheduler, settings: Settings) -> list[ClientWorker]:
    """Create ClientWorkers and register them as scheduler jobs."""
    import aiohttp
    from aiohttp import ClientTimeout
    from shared.services.deye_api import BaseDeyeClient
    from .state_store import StateStore

    timeout = ClientTimeout(total=settings.timeout)
    session = aiohttp.ClientSession(timeout=timeout)
    state_store = StateStore(settings.state_path)

    clients = load_clients(settings.clients_path, settings)
    if not clients:
        logger.error("No clients loaded")
        return []

    workers = []
    for client in clients:
        deye_client = BaseDeyeClient(client.deye, session)
        worker = ClientWorker(client, deye_client, session, state_store, settings)
        workers.append(worker)
        poll_interval = client.poll_interval or settings.poll_interval
        create_client_job(scheduler, worker, poll_interval, client.client_id)

    return workers


async def shutdown_scheduler(scheduler: AsyncIOScheduler, workers: list[ClientWorker]) -> None:
    """Shutdown scheduler and cleanup workers."""
    logger.info("Shutting down scheduler...")
    scheduler.shutdown(wait=False)

    # Close worker resources
    for worker in workers:
        if hasattr(worker, 'session') and worker.session:
            await worker.session.close()
        if hasattr(worker, 'deye_client') and worker.deye_client:
            await worker.deye_client.close()

    logger.info("Scheduler shutdown complete")