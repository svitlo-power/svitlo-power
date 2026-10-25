from typing import Any, Optional
from beanie import Document
from pydantic import AliasChoices, BaseModel, ConfigDict, Field, model_validator

from .localizable_value import LocalizableValue

LEGACY_YASNO_REGION_NAME = "Kyiv"
LEGACY_YASNO_REGION_ID = 25
LEGACY_YASNO_PROVIDER_NAME = "Yasno"
LEGACY_YASNO_PROVIDER_ID = 902


class OutagesScheduleConfig(BaseModel):
    enable: bool = False
    region_id: Optional[int | str] = Field(
        None,
        alias="regionId",
        validation_alias=AliasChoices("regionId", "region_id", "region"),
    )
    dso_id: Optional[int | str] = Field(
        None,
        alias="dsoId",
        validation_alias=AliasChoices("dsoId", "dso_id", "dso"),
    )
    queue: Optional[str] = None

    @model_validator(mode="after")
    def validate_enabled_configuration(self):
        has_location = all(
            isinstance(value, int) and not isinstance(value, bool) and value > 0
            or isinstance(value, str) and bool(value.strip())
            for value in (self.region_id, self.dso_id)
        )
        if self.enable and not (has_location and self.queue and self.queue.strip()):
            raise ValueError("Enabled outages schedule requires region, DSO, and queue")
        return self

    model_config = ConfigDict(populate_by_name=True, serialize_by_alias=True)

    @model_validator(mode="before")
    @classmethod
    def accept_legacy_names(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            return value
        if "regionId" not in value and "region_id" not in value and "region" in value:
            value = dict(value)
            value["regionId"] = value.pop("region")
        if "dsoId" not in value and "dso_id" not in value and "dso" in value:
            value = dict(value)
            value["dsoId"] = value.pop("dso")
        return value


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
                    "regionId": LEGACY_YASNO_REGION_NAME,
                    "dsoId": LEGACY_YASNO_PROVIDER_NAME,
                    "queue": value.get("outages_schedule_queue"),
                }
                if enabled
                else {"enable": False, "region": None, "dso": None, "queue": None}
            )
        return value

    class Settings:
        name = "dashboard_config"
