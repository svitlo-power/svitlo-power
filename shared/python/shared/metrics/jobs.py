"""Scheduled job metrics."""
from prometheus_client import Counter, Gauge, Histogram

# Job execution duration
JOB_EXECUTION_DURATION = Histogram(
    "job_execution_duration_seconds",
    "Scheduled job execution duration",
    ["job_id", "service"],
    buckets=[0.1, 0.5, 1.0, 5.0, 10.0, 30.0, 60.0, 300.0],
)

# Job execution success
JOB_EXECUTION_SUCCESS = Counter(
    "job_execution_success_total",
    "Total number of successful job executions",
    ["job_id", "service"],
)

# Job execution failure
JOB_EXECUTION_FAILURE = Counter(
    "job_execution_failure_total",
    "Total number of failed job executions",
    ["job_id", "service", "error_type"],
)
