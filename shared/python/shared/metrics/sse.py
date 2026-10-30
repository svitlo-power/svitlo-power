"""SSE connection and event metrics."""
from prometheus_client import Counter, Gauge, Histogram

# Total SSE connections established
SSE_CONNECTIONS_TOTAL = Counter(
    "sse_connections_total",
    "Total number of SSE connections established",
    ["service", "auth_type"],
)

# Currently active SSE connections
SSE_CONNECTIONS_ACTIVE = Gauge(
    "sse_connections_active",
    "Currently active SSE connections",
    ["service", "auth_type"],
)

# SSE event delivery latency
SSE_EVENT_DELIVERY_LATENCY = Histogram(
    "sse_event_delivery_latency_seconds",
    "SSE event delivery latency from publish to client delivery",
    ["service", "event_type"],
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0],
)

# SSE reconnects
SSE_RECONNECTS_TOTAL = Counter(
    "sse_reconnects_total",
    "Total number of SSE reconnects",
    ["service"],
)

# SSE unexpected disconnects
SSE_DISCONNECTS_TOTAL = Counter(
    "sse_disconnects_total",
    "Total number of unexpected SSE disconnects",
    ["service", "reason"],
)

# SSE events published
SSE_EVENTS_PUBLISHED = Counter(
    "sse_events_published_total",
    "Total number of SSE events published",
    ["service", "event_type", "channel"],
)