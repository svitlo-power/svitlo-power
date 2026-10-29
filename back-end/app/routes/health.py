"""Health check routes for back-end."""
from fastapi import FastAPI, Depends
from fastapi_injector import Injected
from shared.health import health_registry, HealthCheckResult, HealthStatus
from shared.metrics import (
    DASHBOARD_SNAPSHOT_EPOCH,
    DASHBOARD_SNAPSHOT_VERSION,
    DASHBOARD_SNAPSHOT_AGE_SECONDS,
)
from shared.services.events.service import EventsService
from shared.services.dashboard import ReadOnlyDashboardService
from app.settings import Settings
import time


def register_health_checks(settings: Settings, injector):
    """Register health checks for back-end."""
    
    async def check_dashboard_snapshot():
        """Check dashboard snapshot freshness."""
        try:
            epoch = DASHBOARD_SNAPSHOT_EPOCH._value.get()
            version = DASHBOARD_SNAPSHOT_VERSION._value.get()
            age = DASHBOARD_SNAPSHOT_AGE_SECONDS._value.get()
            
            if epoch == 0 or version == 0:
                return HealthCheckResult(
                    status=HealthStatus.UNHEALTHY,
                    component="dashboard_snapshot",
                    message="No snapshot published yet",
                )
            
            if age > 600:  # 10 minutes
                return HealthCheckResult(
                    status=HealthStatus.UNHEALTHY,
                    component="dashboard_snapshot",
                    message=f"Snapshot stale: {age:.0f}s old",
                    details={"epoch": epoch, "version": version, "age_seconds": age},
                )
            elif age > 300:  # 5 minutes
                return HealthCheckResult(
                    status=HealthStatus.DEGRADED,
                    component="dashboard_snapshot",
                    message=f"Snapshot aging: {age:.0f}s old",
                    details={"epoch": epoch, "version": version, "age_seconds": age},
                )
            
            return HealthCheckResult(
                status=HealthStatus.HEALTHY,
                component="dashboard_snapshot",
                details={"epoch": epoch, "version": version, "age_seconds": age},
            )
        except Exception as e:
            return HealthCheckResult(
                status=HealthStatus.UNHEALTHY,
                component="dashboard_snapshot",
                message=str(e),
            )
    
    async def check_redis():
        """Check Redis connectivity."""
        try:
            events: EventsService = injector.get(EventsService)
            # Check if transport is Redis and connected
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
    
    async def check_sse():
        """Check SSE service."""
        try:
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

    async def check_scheduler():
        """Check scheduler status."""
        try:
            from apscheduler.schedulers.asyncio import AsyncIOScheduler
            scheduler: AsyncIOScheduler = injector.get(AsyncIOScheduler)
            jobs = scheduler.get_jobs()
            
            job_details = []
            for job in jobs:
                job_details.append({
                    "id": job.id,
                    "next_run": job.next_run_time.isoformat() if job.next_run_time else None,
                })
            
            return HealthCheckResult(
                status=HealthStatus.HEALTHY,
                component="scheduler",
                details={"jobs": job_details, "running": scheduler.running},
            )
        except Exception as e:
            return HealthCheckResult(
                status=HealthStatus.UNHEALTHY,
                component="scheduler",
                message=str(e),
            )

    async def check_mongodb():
        """Check MongoDB connectivity."""
        try:
            from beanie import init_beanie
            # Just check if we can access the database
            dashboard: ReadOnlyDashboardService = injector.get(ReadOnlyDashboardService)
            await dashboard.get_buildings(all=True)
            return HealthCheckResult(
                status=HealthStatus.HEALTHY,
                component="mongodb",
                details={"connected": True},
            )
        except Exception as e:
            return HealthCheckResult(
                status=HealthStatus.UNHEALTHY,
                component="mongodb",
                message=str(e),
            )

    # Register all checks
    health_registry.register("dashboard_snapshot", check_dashboard_snapshot)
    health_registry.register("redis", check_redis)
    health_registry.register("sse", check_sse)
    health_registry.register("scheduler", check_scheduler)
    health_registry.register("mongodb", check_mongodb)


def register(app: FastAPI):
    """Register health check endpoints."""

    @app.get("/health")
    async def health():
        """Overall health check."""
        return await health_registry.run_all()

    @app.get("/health/live")
    async def liveness():
        """Liveness probe - always returns healthy if process is running."""
        return {"status": "alive", "timestamp": time.time()}

    @app.get("/health/ready")
    async def readiness():
        """Readiness probe - checks critical dependencies."""
        result = await health_registry.run_all()
        # For readiness, we only care about critical components
        critical = ["mongodb", "redis"]
        ready = all(
            result["checks"].get(c, {}).get("status") == "healthy"
            for c in critical
        )
        return {
            "status": "ready" if ready else "not_ready",
            "checks": {k: v for k, v in result["checks"].items() if k in critical},
            "timestamp": time.time(),
        }

    @app.get("/health/dashboard-snapshot")
    async def dashboard_snapshot_health():
        """Detailed dashboard snapshot health."""
        result = await health_registry.run_all()
        snapshot_check = result["checks"].get("dashboard_snapshot", {})
        return {
            "status": snapshot_check.get("status", "unknown"),
            "component": "dashboard_snapshot",
            "details": snapshot_check.get("details", {}),
            "timestamp": time.time(),
        }