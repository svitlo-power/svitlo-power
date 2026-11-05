"""Metrics for app-back-end dashboard snapshot consumption and shadow reads."""

from prometheus_client import Counter, Gauge, Histogram

APP_BACKEND_SHADOW_PARITY_MISMATCHES = Counter(
    "app_backend_shadow_parity_mismatches_total",
    "Field-level differences found by app-back-end shadow comparisons",
    ["path"],
)

APP_BACKEND_SHADOW_PARITY_LATENCY_DELTA_MS = Histogram(
    "app_backend_shadow_parity_latency_delta_ms",
    "Legacy dashboard calculation time saved by serving a snapshot",
    ["endpoint"],
    buckets=[1, 5, 10, 25, 50, 100, 250, 500, 1000, 5000],
)

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
