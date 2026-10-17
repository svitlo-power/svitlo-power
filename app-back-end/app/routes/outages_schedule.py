from fastapi import FastAPI, HTTPException, Path
from fastapi_injector import Injected
from shared.services import OutagesScheduleService


def register(app: FastAPI):
    @app.get("/api/outagesSchedule/outagesSchedule/{queue}")
    async def get_outages_schedule(
        queue: str = Path(..., description="Queue name"),
        outages_schedule=Injected(OutagesScheduleService),
    ):
        """Outage schedule for a queue - Android endpoint"""
        sched = await outages_schedule.get_schedule_async(queue)
        if sched is None or queue not in sched.root:
            raise HTTPException(status_code=404, detail=f"No schedule found for queue {queue}")
        # Return unwrapped UnitSchedule data (days array) as expected by front-end
        return sched.root[queue].model_dump()