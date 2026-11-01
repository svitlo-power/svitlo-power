from fastapi import FastAPI, HTTPException, Path
from fastapi_injector import Injected
from shared.services import OutagesScheduleService
from shared.features import feature_flags, FeatureFlag
from app.clients.dashboard_snapshot_client import DashboardSnapshotClient


def register(app: FastAPI):
    @app.get("/api/outagesSchedule/outagesSchedule/{queue}")
    async def get_outages_schedule(
        queue: str = Path(..., description="Queue name"),
        outages_schedule=Injected(OutagesScheduleService),
        snapshot_client=Injected(DashboardSnapshotClient),
    ):
        """Outage schedule for a queue - Android endpoint"""
        if feature_flags.is_enabled(FeatureFlag.APP_BACKEND_REDIS_READS):
            sched = snapshot_client.get_outages_schedule(queue)
            if sched is None:
                raise HTTPException(status_code=404, detail=f"No schedule found for queue {queue}")
            return sched.model_dump(by_alias=True)
        sched = await outages_schedule.get_schedule_async(queue)
        if sched is None or queue not in sched.root:
            raise HTTPException(status_code=404, detail=f"No schedule found for queue {queue}")
        # Return unwrapped UnitSchedule data (days array) as expected by front-end
        return sched.root[queue].model_dump()