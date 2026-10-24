from typing import Optional

from beanie import Document, iterative_migration
from shared.models.dashboard_config import DashboardConfig as NewDashboardConfig
from shared.models.dashboard_config import OutagesScheduleConfig
from shared.models.localizable_value import LocalizableValue


class OldDashboardConfig(Document):
    title: LocalizableValue
    enable_outages_schedule: bool = False
    outages_schedule_queue: Optional[str] = None

    class Settings:
        name = "dashboard_config"


class Forward:
    @iterative_migration()
    async def nest_outages_schedule(
        self,
        input_document: OldDashboardConfig,
        output_document: NewDashboardConfig,
    ):
        output_document.title = input_document.title
        if input_document.enable_outages_schedule:
            output_document.outages_schedule = OutagesScheduleConfig(
                enable=True,
                region="Kyiv",
                dso="Yasno",
                queue=input_document.outages_schedule_queue,
            )
        else:
            output_document.outages_schedule = OutagesScheduleConfig(
                enable=False,
                region=None,
                dso=None,
                queue=None,
            )


class Backward:
    @iterative_migration()
    async def flatten_outages_schedule(
        self,
        input_document: NewDashboardConfig,
        output_document: OldDashboardConfig,
    ):
        output_document.title = input_document.title
        schedule = input_document.outages_schedule
        output_document.enable_outages_schedule = bool(schedule and schedule.enable)
        output_document.outages_schedule_queue = schedule.queue if schedule else None
