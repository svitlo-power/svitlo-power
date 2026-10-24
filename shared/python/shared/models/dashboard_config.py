from typing import Any, Optional
from beanie import Document
from pydantic import BaseModel, ConfigDict, Field, model_validator

from .localizable_value import LocalizableValue


class OutagesScheduleConfig(BaseModel):
    enable: bool = False
    region: Optional[str] = None
    dso: Optional[str] = None
    queue: Optional[str] = None

    @model_validator(mode="after")
    def validate_enabled_configuration(self):
        if self.enable and not all(
            value and value.strip() for value in (self.region, self.dso, self.queue)
        ):
            raise ValueError("Enabled outages schedule requires region, DSO, and queue")
        return self

    model_config = ConfigDict(populate_by_name=True)


class DashboardConfig(Document):
    title: LocalizableValue
    outages_schedule: Optional[OutagesScheduleConfig] = None
    enable_outages_schedule: bool = Field(False, exclude=True)
    outages_schedule_queue: Optional[str] = Field(None, exclude=True)

    @model_validator(mode="before")
    @classmethod
    def migrate_legacy_outages_schedule(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            return value

        has_legacy_schedule = (
            "enable_outages_schedule" in value or "outages_schedule_queue" in value
        )
        if value.get("outages_schedule") is None and has_legacy_schedule:
            value = dict(value)
            enabled = value.get("enable_outages_schedule", False)
            value["outages_schedule"] = (
                {
                    "enable": True,
                    "region": "Kyiv",
                    "dso": "Yasno",
                    "queue": value.get("outages_schedule_queue"),
                }
                if enabled
                else {"enable": False, "region": None, "dso": None, "queue": None}
            )
        return value

    class Settings:
        name = "dashboard_config"
