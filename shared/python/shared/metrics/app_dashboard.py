"""Metrics for app-back-end dashboard snapshot consumption."""

from prometheus_client import Counter, Gauge

REDIS_SNAPSHOT_VERSION_LAG = Gauge(
    "redis_snapshot_version_lag",
    "Number of snapshot versions the app-back-end consumer is behind Redis",
)

REDIS_SNAPSHOT_AGE_SECONDS = Gauge(
    "redis_snapshot_age_seconds",
    "Age of the app-back-end's locally cached dashboard snapshot",
)

REDIS_SNAPSHOT_RECONCILIATION_TOTAL = Counter(
    "redis_snapshot_reconciliation_total",
    "Dashboard snapshot reconciliation outcomes",
    ["result"],
)

REDIS_SNAPSHOT_CACHE_MISS_TOTAL = Counter(
    "redis_snapshot_cache_miss_total",
    "Dashboard snapshot Redis cache misses",
)
