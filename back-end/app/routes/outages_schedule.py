from fastapi import FastAPI, HTTPException, Path
from fastapi_injector import Injected
from shared.services import OutagesScheduleService

def register(app: FastAPI):
    @app.get("/api/outagesSchedule/outagesSchedule/{queue}")
    async def get_outages_schedule(
        queue: str = Path(..., description="Queue name"),
        outages_schedule = Injected(OutagesScheduleService),    
    ):
        sched = await outages_schedule.get_schedule_async(queue)
        if sched is None:
            raise HTTPException(status_code=404, detail=f"No schedule found for queue {queue}")
        return sched.model_dump()
