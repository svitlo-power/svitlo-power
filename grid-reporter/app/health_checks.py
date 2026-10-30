"""Health checks for grid-reporter."""
from shared.health import health_registry, HealthCheckResult, HealthStatus
from .service import load_clients
from .settings import load_settings
from .state_store import StateStore


def register_health_checks():
    """Register health checks for grid-reporter."""
    
    async def check_deye_clients():
        """Check Deye API clients."""
        try:
            settings = load_settings()
            clients = load_clients(settings.clients_path, settings)
            
            return HealthCheckResult(
                status=HealthStatus.HEALTHY,
                component="deye_clients",
                details={"clients_loaded": len(clients)},
            )
        except Exception as e:
            return HealthCheckResult(
                status=HealthStatus.UNHEALTHY,
                component="deye_clients",
                message=str(e),
            )
    
    async def check_state_store():
        """Check state store."""
        try:
            settings = load_settings()
            state_store = StateStore(settings.state_path)
            return HealthCheckResult(
                status=HealthStatus.HEALTHY,
                component="state_store",
                details={"path": settings.state_path},
            )
        except Exception as e:
            return HealthCheckResult(
                status=HealthStatus.UNHEALTHY,
                component="state_store",
                message=str(e),
            )
    
    # Register all checks
    health_registry.register("deye_clients", check_deye_clients)
    health_registry.register("state_store", check_state_store)