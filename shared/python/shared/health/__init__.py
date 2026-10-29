"""Health check utilities."""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from enum import Enum


class HealthStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


@dataclass
class HealthCheckResult:
    status: HealthStatus
    component: str
    message: Optional[str] = None
    details: Optional[dict] = None
    timestamp: datetime = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow()

    def to_dict(self) -> dict:
        result = {
            "status": self.status.value,
            "component": self.component,
            "timestamp": self.timestamp.isoformat() + "Z",
        }
        if self.message:
            result["message"] = self.message
        if self.details:
            result["details"] = self.details
        return result


class HealthCheckRegistry:
    """Registry for health checks."""

    def __init__(self):
        self._checks = {}

    def register(self, name: str, check_func):
        """Register a health check function."""
        self._checks[name] = check_func

    async def run_all(self) -> dict:
        """Run all registered health checks."""
        results = {}
        overall_status = HealthStatus.HEALTHY

        for name, check_func in self._checks.items():
            try:
                result = await check_func()
                if isinstance(result, HealthCheckResult):
                    results[name] = result.to_dict()
                    if result.status == HealthStatus.UNHEALTHY:
                        overall_status = HealthStatus.UNHEALTHY
                    elif result.status == HealthStatus.DEGRADED and overall_status == HealthStatus.HEALTHY:
                        overall_status = HealthStatus.DEGRADED
                else:
                    results[name] = {"status": "unknown", "component": name}
            except Exception as e:
                results[name] = {
                    "status": HealthStatus.UNHEALTHY.value,
                    "component": name,
                    "message": str(e),
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                }
                overall_status = HealthStatus.UNHEALTHY

        return {
            "status": overall_status.value,
            "checks": results,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }


# Global registry instance
health_registry = HealthCheckRegistry()