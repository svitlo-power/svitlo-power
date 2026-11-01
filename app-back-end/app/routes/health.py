"""Health check routes for app-back-end."""
from fastapi import FastAPI
from shared.health import health_registry, HealthCheckResult, HealthStatus
from shared.metrics import (
    DASHBOARD_SNAPSHOT_EPOCH,
    DASHBOARD_SNAPSHOT_VERSION,
    DASHBOARD_SNAPSHOT_AGE_SECONDS,
)
from shared.services.dashboard import ReadOnlyDashboardService
from app.clients.dashboard_snapshot_client import DashboardSnapshotClient
import time


def register_health_checks(injector):
    """Register health checks for app-back-end."""
    
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
            import redis.asyncio as redis
            redis_client: redis.Redis = injector.get(redis.Redis)
            await redis_client.ping()
            return HealthCheckResult(
                status=HealthStatus.HEALTHY,
                component="redis",
                details={"connected": True},
            )
        except Exception as e:
            return HealthCheckResult(
                status=HealthStatus.UNHEALTHY,
                component="redis",
                message=str(e),
            )
    
    async def check_mongodb():
        """Check MongoDB connectivity."""
        try:
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
    health_registry.register("mongodb", check_mongodb)


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

    @app.get("/health/redis-dashboard")
    async def redis_dashboard_health():
        """Redis dashboard snapshot health (Phase 2)."""
        import json
        
        injector = app.state.injector
        try:
            client: DashboardSnapshotClient = injector.get(DashboardSnapshotClient)
        except Exception:
            client = None
        
        if client is None:
            return {
                "status": "unhealthy",
                "localEpoch": None,
                "localVersion": None,
                "redisEpoch": None,
                "redisVersion": None,
                "versionLag": None,
                "snapshotAgeSeconds": None,
                "isStale": True,
                "subscribed": False,
                "lastNotificationAt": None,
                "error": "DashboardSnapshotClient not available",
            }
        
        snapshot = client.get_snapshot()
        local_epoch = client.epoch
        local_version = client.version
        is_stale = client.is_stale
        age_seconds = client.age_seconds
        subscribed = client.subscribed
        last_notification = client._last_notification_at
        
        # Get Redis values for comparison
        redis_epoch = None
        redis_version = None
        try:
            snapshot_json = await client._redis.get("cache:dashboard:v1:global")
            if snapshot_json:
                data = json.loads(snapshot_json)
                redis_epoch = data.get("epoch")
                redis_version = data.get("version")
        except Exception:
            pass
        
        version_lag = None
        if redis_version is not None and local_version is not None:
            version_lag = redis_version - local_version
        
        # Determine health status
        unhealthy = False
        degraded = False
        if version_lag is not None and version_lag > 1:
            unhealthy = True
        if not subscribed:
            unhealthy = True
        if age_seconds > 600:
            unhealthy = True
        elif age_seconds > 300:
            degraded = True
        if local_epoch is not None and redis_epoch is not None and local_epoch != redis_epoch:
            unhealthy = True
        
        if unhealthy:
            status = "unhealthy"
        elif degraded:
            status = "degraded"
        else:
            status = "healthy"
        
        return {
            "status": status,
            "localEpoch": local_epoch,
            "localVersion": local_version,
            "redisEpoch": redis_epoch,
            "redisVersion": redis_version,
            "versionLag": version_lag,
            "snapshotAgeSeconds": round(age_seconds, 1) if age_seconds != float("inf") else None,
            "isStale": is_stale,
            "subscribed": subscribed,
            "lastNotificationAt": last_notification.isoformat() + "Z" if last_notification else None,
        }