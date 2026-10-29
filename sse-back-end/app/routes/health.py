"""Health check routes for sse-back-end."""
from fastapi import FastAPI
from shared.health import health_registry, HealthCheckResult, HealthStatus
from shared.metrics import (
    SSE_CONNECTIONS_ACTIVE,
    SSE_CONNECTIONS_TOTAL,
)
import time


def register_health_checks(injector):
    """Register health checks for sse-back-end."""

    async def check_sse():
        """Check SSE service."""
        try:
            from shared.services.events.service import EventsService
            events: EventsService = injector.get(EventsService)
            public_clients = len(events._public_clients)
            private_clients = len(events._private_clients)

            return HealthCheckResult(
                status=HealthStatus.HEALTHY,
                component="sse",
                details={
                    "public_connections": public_clients,
                    "private_connections": private_clients,
                    "total_connections": public_clients + private_clients,
                },
            )
        except Exception as e:
            return HealthCheckResult(
                status=HealthStatus.UNHEALTHY,
                component="sse",
                message=str(e),
            )

    async def check_redis():
        """Check Redis connectivity."""
        try:
            from shared.services.events.service import EventsService
            events: EventsService = injector.get(EventsService)
            if hasattr(events.transport, 'redis'):
                redis = events.transport.redis
                await redis.ping()
                return HealthCheckResult(
                    status=HealthStatus.HEALTHY,
                    component="redis",
                    details={"connected": True},
                )
            else:
                return HealthCheckResult(
                    status=HealthStatus.HEALTHY,
                    component="redis",
                    details={"connected": True, "mode": "local"},
                )
        except Exception as e:
            return HealthCheckResult(
                status=HealthStatus.UNHEALTHY,
                component="redis",
                message=str(e),
            )

    # Register all checks
    health_registry.register("sse", check_sse)
    health_registry.register("redis", check_redis)


def register(app: FastAPI):
    """Register health check endpoints."""

    @app.get("/health")
    async def health():
        """Overall health check."""
        return await health_registry.run_all()

    @app.get("/health/live")
    async def liveness():
        """Liveness probe."""
        return {"status": "alive", "timestamp": time.time()}

    @app.get("/health/ready")
    async def readiness():
        """Readiness probe."""
        result = await health_registry.run_all()
        critical = ["redis"]
        ready = all(
            result["checks"].get(c, {}).get("status") == "healthy"
            for c in critical
        )
        return {
            "status": "ready" if ready else "not_ready",
            "checks": {k: v for k, v in result["checks"].items() if k in critical},
            "timestamp": time.time(),
        }