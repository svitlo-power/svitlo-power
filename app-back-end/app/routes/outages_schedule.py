from fastapi import FastAPI, HTTPException, Path, Request
from fastapi_injector import Injected
from shared.services import OutagesScheduleService
from shared.services.dashboard_snapshot import DashboardSnapshotClient
from app.services import DashboardShadowComparison


def register(app: FastAPI):
    @app.get("/api/outagesSchedule/outagesSchedule/{queue}")
    async def get_outages_schedule(
        request: Request,
        queue: str = Path(..., description="Queue name"),
        outages_schedule=Injected(OutagesScheduleService),
        snapshot_client: DashboardSnapshotClient = Injected(DashboardSnapshotClient),
        shadow: DashboardShadowComparison = Injected(DashboardShadowComparison),
    ):
        """Outage schedule for a queue - Android endpoint"""
        snapshot_schedule = snapshot_client.get_outages_schedule(queue)
        if snapshot_schedule is not None:
            async def legacy_schedule():
                result = await outages_schedule.get_schedule_async(queue)
                return result.root.get(queue) if result else None

            shadow.sample(
                "GET /api/outagesSchedule/outagesSchedule/{queue}",
                legacy_schedule,
                lambda: snapshot_schedule,
            )
            if (
                request.app.state.settings.APP_BACKEND_REDIS_DASHBOARD_ENABLED
                and not snapshot_client.is_stale
            ):
                return snapshot_schedule.model_dump(by_alias=True)

        sched = await outages_schedule.get_schedule_async(queue)
        if sched is None or queue not in sched.root:
            raise HTTPException(status_code=404, detail=f"No schedule found for queue {queue}")
        # Return unwrapped UnitSchedule data (days array) as expected by front-end
        return sched.root[queue].model_dump()