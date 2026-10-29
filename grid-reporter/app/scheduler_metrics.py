"""Scheduler metrics instrumentation for grid-reporter (same as back-end)."""
from datetime import datetime
from time import perf_counter

from apscheduler.events import (
    EVENT_JOB_ERROR,
    EVENT_JOB_EXECUTED,
    EVENT_JOB_MAX_INSTANCES,
    EVENT_JOB_MISSED,
    EVENT_JOB_SUBMITTED,
    EVENT_SCHEDULER_STARTED,
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from shared.metrics import (
    JOB_EXECUTION_DURATION,
    JOB_EXECUTION_FAILURE,
    JOB_EXECUTION_SUCCESS,
)

SERVICE = "grid-reporter"


def register_scheduler_metrics(scheduler: AsyncIOScheduler) -> None:
    """Register APScheduler event listeners for job metrics (same as back-end)."""
    submitted_runs: dict[tuple[str, datetime], float] = {}

    def record_event(event) -> None:
        if event.code == EVENT_SCHEDULER_STARTED:
            for job in scheduler.get_jobs():
                labels = {"job_id": job.id, "service": SERVICE}
                JOB_EXECUTION_DURATION.labels(**labels)
                JOB_EXECUTION_SUCCESS.labels(**labels)
                JOB_EXECUTION_FAILURE.labels(**labels, error_type="none")
            return

        if event.code == EVENT_JOB_SUBMITTED:
            submitted_at = perf_counter()
            for run_time in event.scheduled_run_times:
                submitted_runs[(event.job_id, run_time)] = submitted_at
            return

        if event.code in (EVENT_JOB_EXECUTED, EVENT_JOB_ERROR):
            job_labels = {"job_id": event.job_id, "service": SERVICE}
            started_at = submitted_runs.pop(
                (event.job_id, event.scheduled_run_time), None
            )
            if started_at is not None:
                JOB_EXECUTION_DURATION.labels(**job_labels).observe(
                    perf_counter() - started_at
                )

            if event.code == EVENT_JOB_EXECUTED:
                JOB_EXECUTION_SUCCESS.labels(**job_labels).inc()
            else:
                error_type = (
                    type(event.exception).__name__
                    if event.exception is not None
                    else "unknown"
                )
                JOB_EXECUTION_FAILURE.labels(
                    **job_labels, error_type=error_type
                ).inc()

        elif event.code in (EVENT_JOB_MISSED, EVENT_JOB_MAX_INSTANCES):
            error_type = (
                "misfire"
                if event.code == EVENT_JOB_MISSED
                else "max_instances"
            )
            JOB_EXECUTION_FAILURE.labels(
                job_id=event.job_id,
                service=SERVICE,
                error_type=error_type,
            ).inc(len(getattr(event, "scheduled_run_times", [None])))

    scheduler.add_listener(
        record_event,
        EVENT_JOB_SUBMITTED
        | EVENT_JOB_EXECUTED
        | EVENT_JOB_ERROR
        | EVENT_JOB_MISSED
        | EVENT_JOB_MAX_INSTANCES
        | EVENT_SCHEDULER_STARTED,
    )