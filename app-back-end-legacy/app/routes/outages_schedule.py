from fastapi import FastAPI, HTTPException, Path, Request
from fastapi_injector import Injected
from shared.services import OutagesScheduleService
from shared.services.dashboard_snapshot import DashboardSnapshotClient
from app.snapshot_mode import active_dashboard_snapshot


def register(app: FastAPI):
    @app.get("/api/outagesSchedule/outagesSchedule/{queue}")
    async def get_outages_schedule(
        request: Request,
        queue: str = Path(..., description="Queue name"),
        outages_schedule=Injected(OutagesScheduleService),
        snapshot_client: DashboardSnapshotClient = Injected(DashboardSnapshotClient),
    ):
        """Outage schedule for a queue - Android endpoint"""
        snapshot = active_dashboard_snapshot(request, snapshot_client)
        snapshot_schedule = (
            snapshot_client.get_outages_schedule(queue)
            if snapshot is not None
            else None
        )
        if snapshot_schedule is not None:
            return snapshot_schedule.model_dump(by_alias=True)

        sched = await outages_schedule.get_schedule_async(queue)
        if sched is None or queue not in sched.root:
            raise HTTPException(status_code=404, detail=f"No schedule found for queue {queue}")
        # Return unwrapped UnitSchedule data (days array) as expected by front-end
        return sched.root[queue].model_dump()