"""Redis connection and operation metrics."""
from prometheus_client import Counter, Gauge, Histogram

# Redis connection status (1 = connected, 0 = disconnected)
REDIS_CONNECTION_STATUS = Gauge(
    "redis_connection_status",
    "Redis connection status (1 = connected, 0 = disconnected)",
    ["service"],
)

# Redis pub/sub latency in seconds
REDIS_PUBSUB_LATENCY = Histogram(
    "redis_pubsub_latency_seconds",
    "Redis pub/sub message delivery latency",
    ["channel"],
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0],
)

# Redis lease status (1 = held, 0 = not held)
REDIS_LEASE_STATUS = Gauge(
    "redis_lease_status",
    "Redis lease status (1 = held by this instance, 0 = not held)",
    ["lease_key"],
)

# Redis operation duration
REDIS_OPERATION_DURATION = Histogram(
    "redis_operation_duration_seconds",
    "Redis operation duration",
    ["operation", "service"],
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0],
)

# Redis operation errors
REDIS_OPERATION_ERRORS = Counter(
    "redis_operation_errors_total",
    "Total number of Redis operation errors",
    ["operation", "service", "error_type"],
)