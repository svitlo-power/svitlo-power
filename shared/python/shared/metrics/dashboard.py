"""Dashboard snapshot metrics."""
from prometheus_client import Counter, Gauge, Histogram

# Dashboard snapshot build duration in seconds
DASHBOARD_SNAPSHOT_BUILD_DURATION = Histogram(
    "dashboard_snapshot_build_duration_seconds",
    "Time spent building dashboard snapshot",
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0],
)

# Dashboard snapshot publish duration in seconds
DASHBOARD_SNAPSHOT_PUBLISH_DURATION = Histogram(
    "dashboard_snapshot_publish_duration_seconds",
    "Time spent publishing dashboard snapshot to Redis",
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0],
)

# Current snapshot epoch (producer start time in ms)
DASHBOARD_SNAPSHOT_EPOCH = Gauge(
    "dashboard_snapshot_epoch",
    "Current dashboard snapshot epoch (producer start time in milliseconds)",
)

# Current snapshot version within epoch
DASHBOARD_SNAPSHOT_VERSION = Gauge(
    "dashboard_snapshot_version",
    "Current dashboard snapshot version within epoch",
)

# Snapshot age in seconds (now - generatedAt)
DASHBOARD_SNAPSHOT_AGE_SECONDS = Gauge(
    "dashboard_snapshot_age_seconds",
    "Age of current dashboard snapshot in seconds",
)

# Snapshot write errors
DASHBOARD_SNAPSHOT_WRITE_ERRORS = Counter(
    "dashboard_snapshot_write_errors_total",
    "Total number of dashboard snapshot write errors",
    ["error_type"],
)

# Refresh requests
DASHBOARD_REFRESH_REQUESTS = Counter(
    "dashboard_refresh_requests_total",
    "Total number of dashboard refresh requests",
    ["reason"],
)

# Coalesced refresh requests
DASHBOARD_REFRESH_COALESCED = Counter(
    "dashboard_refresh_coalesced_total",
    "Total number of coalesced refresh requests",
)

# Parity mismatches between legacy API and Redis snapshot
DASHBOARD_PARITY_MISMATCHES = Counter(
    "dashboard_parity_mismatches_total",
    "Total number of parity mismatches between legacy API and Redis snapshot",
    ["field_path"],
)