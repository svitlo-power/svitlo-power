from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock

from apscheduler.events import (
    EVENT_JOB_ERROR,
    EVENT_JOB_EXECUTED,
    EVENT_JOB_SUBMITTED,
    EVENT_SCHEDULER_STARTED,
)

from app.scheduler_metrics import SERVICE, register_scheduler_metrics
from shared.metrics import (
    JOB_EXECUTION_DURATION,
    JOB_EXECUTION_FAILURE,
    JOB_EXECUTION_SUCCESS,
)


def _counter_value(metric, **labels):
    return metric.labels(**labels)._value.get()


def test_scheduler_metrics_record_execution():
    scheduler = MagicMock()
    run_at = datetime.now(timezone.utc)
    scheduler.get_jobs.return_value = [
        SimpleNamespace(id="metrics_test_success", next_run_time=None)
    ]
    listeners = {}
    scheduler.add_listener.side_effect = lambda callback, events: listeners.update(
        callback=callback,
        events=events,
    )
    labels = {"job_id": "metrics_test_success", "service": SERVICE}
    success_before = _counter_value(JOB_EXECUTION_SUCCESS, **labels)
    duration_before = JOB_EXECUTION_DURATION.labels(**labels)._sum.get()

    register_scheduler_metrics(scheduler)
    listener = listeners["callback"]
    listener(SimpleNamespace(code=EVENT_SCHEDULER_STARTED))
    assert _counter_value(JOB_EXECUTION_SUCCESS, **labels) == success_before
    assert (
        _counter_value(
            JOB_EXECUTION_FAILURE,
            **labels,
            error_type="none",
        )
        == 0
    )
    listener(
        SimpleNamespace(
            code=EVENT_JOB_SUBMITTED,
            job_id=labels["job_id"],
            scheduled_run_times=[run_at],
        )
    )
    listener(
        SimpleNamespace(
            code=EVENT_JOB_EXECUTED,
            job_id=labels["job_id"],
            scheduled_run_time=run_at,
        )
    )

    assert _counter_value(JOB_EXECUTION_SUCCESS, **labels) == success_before + 1
    assert JOB_EXECUTION_DURATION.labels(**labels)._sum.get() > duration_before


def test_scheduler_metrics_record_failures():
    scheduler = MagicMock()
    listeners = {}
    scheduler.add_listener.side_effect = lambda callback, events: listeners.update(
        callback=callback,
        events=events,
    )
    labels = {"job_id": "metrics_test_failure", "service": SERVICE}
    error_labels = {**labels, "error_type": "ValueError"}
    failure_before = _counter_value(JOB_EXECUTION_FAILURE, **error_labels)

    register_scheduler_metrics(scheduler)
    listener = listeners["callback"]
    listener(
        SimpleNamespace(
            code=EVENT_JOB_ERROR,
            job_id=labels["job_id"],
            scheduled_run_time=datetime.now(timezone.utc),
            exception=ValueError("job failed"),
        )
    )

    assert _counter_value(JOB_EXECUTION_FAILURE, **error_labels) == failure_before + 1
