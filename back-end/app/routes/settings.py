from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from beanie import PydanticObjectId

from shared.models.system_setting import SystemSetting
from shared.services.settings.service import SettingsService
from app.services.authorization import AuthorizationService
from app.models.api.users import UserListResponseModel


router = APIRouter(prefix="/settings", tags=["settings"])


class SettingResponse(BaseModel):
    key: str
    label: str
    description: str
    setting_type: str
    default_value: Any
    value: Optional[Any]
    validation: Optional[Dict[str, Any]]
    category: str
    created_at: str
    updated_at: str

    @classmethod
    def from_model(cls, setting: SystemSetting) -> "SettingResponse":
        return cls(
            key=setting.key,
            label=setting.label,
            description=setting.description,
            setting_type=setting.setting_type,
            default_value=setting.default_value,
            value=setting.value,
            validation=setting.validation,
            category=setting.category,
            created_at=setting.created_at.isoformat() if setting.created_at else "",
            updated_at=setting.updated_at.isoformat() if setting.updated_at else "",
        )


class SettingUpdateRequest(BaseModel):
    value: Any


class BulkUpdateRequest(BaseModel):
    updates: Dict[str, Any]


class SettingsGroupedResponse(BaseModel):
    categories: Dict[str, List[SettingResponse]]


@router.get("", response_model=SettingsGroupedResponse)
async def get_all_settings(
    current_user: UserListResponseModel = Depends(AuthorizationService.get_current_user),
    settings_service: SettingsService = Depends(),
):
    """Get all settings grouped by category."""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    grouped = await settings_service.get_settings_grouped_by_category()
    result = {}
    for category, settings in grouped.items():
        result[category] = [SettingResponse.from_model(s) for s in settings]
    
    return SettingsGroupedResponse(categories=result)


@router.get("/{key}", response_model=SettingResponse)
async def get_setting(
    key: str,
    current_user: UserListResponseModel = Depends(AuthorizationService.get_current_user),
    settings_service: SettingsService = Depends(),
):
    """Get a single setting by key."""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    setting = await settings_service.get_setting(key)
    if not setting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Setting '{key}' not found"
        )
    
    return SettingResponse.from_model(setting)


@router.put("/{key}", response_model=SettingResponse)
async def update_setting(
    key: str,
    request: SettingUpdateRequest,
    current_user: UserListResponseModel = Depends(AuthorizationService.get_current_user),
    settings_service: SettingsService = Depends(),
):
    """Update a setting value."""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    setting = await settings_service.set_value(key, request.value)
    if not setting:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Setting '{key}' not found"
        )
    
    return SettingResponse.from_model(setting)


@router.post("/bulk", response_model=Dict[str, bool])
async def bulk_update_settings(
    request: BulkUpdateRequest,
    current_user: UserListResponseModel = Depends(AuthorizationService.get_current_user),
    settings_service: SettingsService = Depends(),
):
    """Bulk update multiple settings."""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    results = await settings_service.bulk_update(request.updates)
    return results


@router.post("/reset", response_model=Dict[str, int])
async def reset_settings(
    current_user: UserListResponseModel = Depends(AuthorizationService.get_current_user),
    settings_service: SettingsService = Depends(),
):
    """Reset all settings to their default values."""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required"
        )
    
    count = await settings_service.reset_to_defaults()
    return {"reset_count": count}