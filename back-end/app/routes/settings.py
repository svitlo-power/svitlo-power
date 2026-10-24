from typing import Dict
from fastapi import FastAPI, Depends, HTTPException, status

from shared.services.settings.service import SettingsService
from app.utils.jwt_dependencies import jwt_required
from app.models.api import (
    SettingsGroupedResponse,
    CategorySettingsResponse,
    SettingResponse,
    SettingUpdateRequest,
    SettingBulkUpdateRequest
)


def register(app: FastAPI):

    @app.get("/api/settings", response_model=SettingsGroupedResponse)
    async def get_all_settings(
        current_user=Depends(jwt_required),
        settings_service: SettingsService = Depends(),
    ):
        """Get all settings grouped by category."""
        # if not current_user.is_admin:
        #     raise HTTPException(
        #         status_code=status.HTTP_403_FORBIDDEN,
        #         detail="Admin access required"
        #     )

        grouped = await settings_service.get_settings_grouped_by_category()
        result = {}
        for category_id, data in grouped.items():
            category = data["category"]
            result[category_id] = CategorySettingsResponse(
                id=category_id,
                label=category.label,
                settings=[
                    SettingResponse.from_model(setting)
                    for setting in data["settings"]
                ],
            )

        return SettingsGroupedResponse(categories=result)


    @app.get("/api/settings/{key}", response_model=SettingResponse)
    async def get_setting(
        key: str,
        current_user=Depends(jwt_required),
        settings_service: SettingsService = Depends(),
    ):
        """Get a single setting by key."""
        # if not current_user.is_admin:
        #     raise HTTPException(
        #         status_code=status.HTTP_403_FORBIDDEN,
        #         detail="Admin access required"
        #     )
        
        setting = await settings_service.get_setting(key)
        if not setting:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Setting '{key}' not found"
            )
        
        return SettingResponse.from_model(setting)


    @app.put("/api/settings/{key}", response_model=SettingResponse)
    async def update_setting(
        key: str,
        request: SettingUpdateRequest,
        current_user=Depends(jwt_required),
        settings_service: SettingsService = Depends(),
    ):
        """Update a setting value."""
        # if not current_user.is_admin:
        #     raise HTTPException(
        #         status_code=status.HTTP_403_FORBIDDEN,
        #         detail="Admin access required"
        #     )
        
        setting = await settings_service.set_value(key, request.value)
        if not setting:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Setting '{key}' not found"
            )
        
        return SettingResponse.from_model(setting)


    @app.post("/api/settings/bulk", response_model=Dict[str, bool])
    async def bulk_update_settings(
        request: SettingBulkUpdateRequest,
        current_user=Depends(jwt_required),
        settings_service: SettingsService = Depends(),
    ):
        """Bulk update multiple settings."""
        # if not current_user.is_admin:
        #     raise HTTPException(
        #         status_code=status.HTTP_403_FORBIDDEN,
        #         detail="Admin access required"
        #     )
        
        results = await settings_service.bulk_update(request.updates)
        return results


    @app.post("/api/settings/reset", response_model=Dict[str, int])
    async def reset_settings(
        current_user=Depends(jwt_required),
        settings_service: SettingsService = Depends(),
    ):
        """Reset all settings to their default values."""
        # if not current_user.is_admin:
        #     raise HTTPException(
        #         status_code=status.HTTP_403_FORBIDDEN,
        #         detail="Admin access required"
        #     )
        
        count = await settings_service.reset_to_defaults()
        return {"reset_count": count}
