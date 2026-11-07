import asyncio
import logging
import secrets
from datetime import datetime, timezone

from beanie import PydanticObjectId
from fastapi import APIRouter, Depends, FastAPI, Header, HTTPException, Request, Response
from fastapi_injector import Injected
from prometheus_client import Counter, Histogram

from app.services import PushService
from shared.health import health_registry
from shared.models.api.dashboard import (
    BuildingResponse,
    BuildingsSummaryRequest,
    BuildingSummaryResponse,
    BuildingWithSummaryResponse,
    DashboardConfigResponse,
    PowerLogsRequest,
    PowerLogsResponse,
)
from shared.models.api.push import (
    PushDeviceRegisterRequest,
    PushDeviceResponse,
    PushDeviceSubscriptionsRequest,
    PushDeviceTokenRequest,
    PushTopicResponse,
)
from shared.models.outages_schedule import UnitSchedule
from shared.services import OutagesScheduleService
from shared.services.dashboard import ReadOnlyDashboardService


logger = logging.getLogger(__name__)
READINESS_CHECKS = ("mongodb", "redis")
dependency_calls = Counter(
    "internal_app_dependency_calls_total", "Internal app API dependency calls", ["operation", "outcome"]
)
dependency_duration = Histogram(
    "internal_app_dependency_duration_seconds", "Internal app API dependency call duration", ["operation"]
)


async def require_internal_token(
    request: Request,
    authorization: str | None = Header(default=None),
):
    token = request.app.state.settings.INTERNAL_API_TOKEN
    if not token:
        raise HTTPException(status_code=503, detail="Internal API is not configured")
    scheme, _, supplied = (authorization or "").partition(" ")
    if scheme.lower() != "bearer" or not secrets.compare_digest(
        supplied.encode("utf-8"), token.encode("utf-8")
    ):
        raise HTTPException(status_code=401, detail="Invalid service credentials")


async def call_service(request: Request, operation):
    name = request.scope["route"].name
    try:
        with dependency_duration.labels(operation=name).time():
            result = await asyncio.wait_for(
                operation, timeout=request.app.state.settings.INTERNAL_API_TIMEOUT_SECONDS
            )
    except asyncio.TimeoutError as error:
        dependency_calls.labels(operation=name, outcome="timeout").inc()
        logger.warning("Internal API dependency timed out: %s", name)
        raise HTTPException(status_code=504, detail="Dependency timed out") from error
    except Exception as error:
        dependency_calls.labels(operation=name, outcome="error").inc()
        logger.error("Internal API dependency failed: %s (%s)", name, type(error).__name__)
        raise HTTPException(status_code=503, detail="Dependency unavailable") from error
    dependency_calls.labels(operation=name, outcome="success").inc()
    return result


def register(app: FastAPI):
    router = APIRouter(prefix="/internal/v1/app", dependencies=[Depends(require_internal_token)])

    @router.get("/health")
    async def health():
        return {"status": "ok"}

    @router.get("/ready")
    async def ready(request: Request, response: Response):
        try:
            result = await asyncio.wait_for(
                health_registry.run_all(), timeout=request.app.state.settings.INTERNAL_API_TIMEOUT_SECONDS
            )
            checks = {
                name: result["checks"].get(name, {}).get("status", "unknown")
                for name in READINESS_CHECKS
            }
        except Exception as error:
            logger.warning("Internal API readiness check failed (%s)", type(error).__name__)
            checks = {name: "unknown" for name in READINESS_CHECKS}
        is_ready = all(status == "healthy" for status in checks.values())
        if not is_ready:
            response.status_code = 503
        return {"status": "ready" if is_ready else "not_ready", "checks": checks}

    @router.get("/dashboard/buildings", response_model=list[BuildingResponse])
    async def get_buildings(request: Request, dashboard=Injected(ReadOnlyDashboardService)):
        return await call_service(request, dashboard.get_buildings(all=False))

    @router.post("/dashboard/buildings/summary", response_model=list[BuildingSummaryResponse])
    async def get_buildings_summary(
        request: Request, body: BuildingsSummaryRequest, dashboard=Injected(ReadOnlyDashboardService)
    ):
        return await call_service(request, dashboard.get_buildings_summary(body.building_ids))

    @router.get("/dashboard/buildings-with-summary", response_model=list[BuildingWithSummaryResponse])
    async def get_buildings_with_summary(request: Request, dashboard=Injected(ReadOnlyDashboardService)):
        return await call_service(request, dashboard.get_buildings_with_summary())

    @router.get("/dashboard/config", response_model=DashboardConfigResponse)
    async def get_config(request: Request, dashboard=Injected(ReadOnlyDashboardService)):
        return await call_service(request, dashboard.get_config())

    @router.post("/dashboard/buildings/{building_id}/power-logs", response_model=PowerLogsResponse)
    async def get_power_logs(
        request: Request, building_id: PydanticObjectId, body: PowerLogsRequest,
        dashboard=Injected(ReadOnlyDashboardService),
    ):
        try:
            start = datetime.fromisoformat(body.start_date.replace("Z", "+00:00"))
            end = datetime.fromisoformat(body.end_date.replace("Z", "+00:00"))
            start = start.replace(tzinfo=timezone.utc) if start.tzinfo is None else start
            end = end.replace(tzinfo=timezone.utc) if end.tzinfo is None else end
            if start >= end:
                raise ValueError("startDate must be before endDate")
        except (AttributeError, TypeError, ValueError) as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
        result = await call_service(request, dashboard.get_power_logs(building_id, start, end))
        if not result:
            raise HTTPException(status_code=404, detail="Building not found or no power logs available")
        return result

    @router.get("/outages-schedule/{queue}", response_model=UnitSchedule)
    async def get_outages_schedule(request: Request, queue: str, schedule=Injected(OutagesScheduleService)):
        result = await call_service(request, schedule.get_schedule_async(queue))
        if result is None or queue not in result.root:
            raise HTTPException(status_code=404, detail="Schedule not found")
        return result.root[queue]

    @router.post("/push/devices", response_model=PushDeviceResponse)
    async def register_device(request: Request, body: PushDeviceRegisterRequest, push=Injected(PushService)):
        return await call_service(request, push.register_device(body))

    @router.post("/push/devices/current", response_model=PushDeviceResponse)
    async def get_device(request: Request, body: PushDeviceTokenRequest, push=Injected(PushService)):
        result = await call_service(request, push.get_device(body.token))
        if result is None:
            raise HTTPException(status_code=404, detail="Device not registered")
        return result

    @router.post("/push/devices/subscriptions", response_model=PushDeviceResponse)
    async def update_subscriptions(
        request: Request, body: PushDeviceSubscriptionsRequest, push=Injected(PushService)
    ):
        result = await call_service(request, push.update_subscriptions(body))
        if result is None:
            raise HTTPException(status_code=404, detail="Device not registered")
        return result

    @router.post("/push/devices/unregister")
    async def unregister_device(request: Request, body: PushDeviceTokenRequest, push=Injected(PushService)):
        await call_service(request, push.unregister_device(body.token))
        return {"success": True}

    @router.get("/push/topics", response_model=list[PushTopicResponse])
    async def get_topics(request: Request, push=Injected(PushService)):
        return await call_service(request, push.get_enabled_topics())

    app.include_router(router)