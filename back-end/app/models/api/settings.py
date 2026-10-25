from typing import Any, Dict, List, Optional

from pydantic import BaseModel
from shared.models.localizable_value import LocalizableValue
from shared.models.system_setting import SystemSetting, SystemSettingValue


class SettingResponse(BaseModel):
    key: str
    label: LocalizableValue
    description: LocalizableValue
    setting_type: str
    default_value: SystemSettingValue
    value: Optional[SystemSettingValue]
    validation: Optional[Dict[str, Any]]
    editable: bool = True
    category_id: str
    created_at: str
    updated_at: str

    @classmethod
    def from_model(cls, setting: SystemSetting) -> "SettingResponse":
        if setting.category_id is None:
            raise ValueError(f"Setting '{setting.key}' has no category reference")
        return cls(
            key=setting.key,
            label=setting.label,
            description=setting.description,
            setting_type=setting.setting_type,
            default_value=setting.default_value,
            value=setting.value,
            validation=setting.validation,
            editable=setting.editable,
            category_id=str(setting.category_id),
            created_at=setting.created_at.isoformat() if setting.created_at else "",
            updated_at=setting.updated_at.isoformat() if setting.updated_at else "",
        )


class SettingUpdateRequest(BaseModel):
    value: SystemSettingValue


class SettingBulkUpdateRequest(BaseModel):
    updates: Dict[str, SystemSettingValue]


class CategorySettingsResponse(BaseModel):
    id: str
    label: LocalizableValue
    settings: List[SettingResponse]


class SettingsGroupedResponse(BaseModel):
    categories: Dict[str, CategorySettingsResponse]


__all__ = [
    "SettingResponse",
    "SettingUpdateRequest",
    "SettingBulkUpdateRequest",
    "SettingsGroupedResponse",
    "CategorySettingsResponse",
]
