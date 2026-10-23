from datetime import datetime
from typing import Literal, Optional, Union
from pydantic import ConfigDict, Field
from beanie import Document


SystemSettingValue = Union[
    int,
    float,
    str,
    bool,
    datetime,
    None,
]


class SystemSetting(Document):
    key: str = Field(..., description="Unique identifier (e.g., 'discharge_target_soc')")
    label: str = Field(..., description="Human-readable label")
    description: str = Field(..., description="Help text")
    setting_type: Literal["number", "text", "datetime", "timestamp", "boolean", "select"] = Field(
        ..., description="Type of setting"
    )
    default_value: SystemSettingValue = Field(..., description="Default value")
    value: Optional[SystemSettingValue] = Field(None, description="Current value (overrides default)")
    validation: Optional[dict] = Field(None, description="Validation rules (min/max for numbers, regex for text, options for select)")
    category: str = Field(..., description="Grouping (e.g., 'power_estimation', 'notifications')")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "system_settings"
        indexes = [
            "key",
            "category",
        ]

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "key": "discharge_target_soc",
                "label": "Discharge Target SOC",
                "description": "Battery % to stop discharging",
                "setting_type": "number",
                "default_value": 10,
                "value": 10,
                "validation": {"min": 0, "max": 100},
                "category": "power_estimation",
            }
        }
    )