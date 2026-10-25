from datetime import datetime
from typing import Any, Literal, Optional, Union
from pydantic import ConfigDict, Field, field_validator
from beanie import Document, PydanticObjectId

from .localizable_value import LocalizableValue


class SystemSettingCategory(Document):
    key: str = Field(..., description="Stable category identifier")
    label: LocalizableValue = Field(..., description="Localized category label")

    class Settings:
        name = "system_setting_categories"
        indexes = ["key"]


SystemSettingValue = Union[
    int,
    float,
    str,
    bool,
    datetime,
    LocalizableValue,
    None,
]


class SystemSetting(Document):
    key: str = Field(..., description="Unique identifier (e.g., 'discharge_target_soc')")
    label: LocalizableValue = Field(..., description="Localized human-readable label")
    description: LocalizableValue = Field(..., description="Localized help text")
    setting_type: Literal[
        "number",
        "text",
        "datetime",
        "timestamp",
        "boolean",
        "select",
        "localizable_text",
    ] = Field(..., description="Type of setting")
    default_value: SystemSettingValue = Field(..., description="Default value")
    value: Optional[SystemSettingValue] = Field(None, description="Current value (overrides default)")
    validation: Optional[dict] = Field(None, description="Validation rules (min/max for numbers, regex for text, options for select)")
    editable: bool = Field(True, description="Whether this setting can be changed in the generic settings UI")
    category_id: Optional[PydanticObjectId] = Field(
        None,
        description="Referenced system setting category",
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    @field_validator("label", "description", mode="before")
    @classmethod
    def convert_legacy_text(cls, value: Any) -> LocalizableValue:
        if isinstance(value, str):
            return LocalizableValue({"en": value})
        return value

    class Settings:
        name = "system_settings"
        indexes = [
            "key",
            "category_id",
        ]

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "key": "discharge_target_soc",
                "label": {"en": "Discharge Target SOC", "uk": "Цільовий рівень заряду"},
                "description": {
                    "en": "Battery % to stop discharging",
                    "uk": "Рівень заряду батареї (%) для припинення розрядження",
                },
                "setting_type": "number",
                "default_value": 10,
                "value": 10,
                "validation": {"min": 0, "max": 100},
                "editable": True,
                "category_id": "64a1a1a1a1a1a1a1a1a1a1a1",
            }
        }
    )