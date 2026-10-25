from beanie import PydanticObjectId

from app.models.api.settings import (
    CategorySettingsResponse,
    SettingResponse,
    SettingsGroupedResponse,
)
from shared.models.localizable_value import LocalizableValue
from shared.models.system_setting import SystemSetting

from app.models.api.settings import SettingUpdateRequest
from app.routes.settings import reject_read_only_setting_update
from fastapi import HTTPException
from unittest.mock import AsyncMock, MagicMock
import pytest


def test_setting_update_request_accepts_localizable_text():
    request = SettingUpdateRequest(value={"en": "Dashboard", "uk": "Панель"})

    assert isinstance(request.value, LocalizableValue)
    assert request.value.root == {"en": "Dashboard", "uk": "Панель"}


@pytest.mark.asyncio
async def test_generic_settings_updates_reject_non_editable_setting():
    settings = MagicMock()
    settings.get_setting = AsyncMock(return_value=MagicMock(editable=False))
    try:
        await reject_read_only_setting_update(settings, "dashboard_outages_schedule_region")
    except HTTPException as error:
        assert error.status_code == 409
    else:
        raise AssertionError("Non-editable settings cannot be changed through generic settings")


@pytest.mark.asyncio
async def test_generic_settings_updates_allow_editable_settings():
    settings = MagicMock()
    settings.get_setting = AsyncMock(return_value=MagicMock(editable=True))

    await reject_read_only_setting_update(settings, "charge_target_soc")


def test_setting_response_includes_localized_metadata_and_category_id():
    category_id = PydanticObjectId("64a1a1a1a1a1a1a1a1a1a1a1")
    setting = SystemSetting(
        key="dashboard_title",
        label=LocalizableValue({"en": "Dashboard title", "uk": "Назва панелі"}),
        description=LocalizableValue({"en": "Title", "uk": "Назва"}),
        setting_type="number",
        default_value=10,
        category_id=category_id,
    )

    response = SettingResponse.from_model(setting)

    assert response.label.root == {"en": "Dashboard title", "uk": "Назва панелі"}
    assert response.description.root == {"en": "Title", "uk": "Назва"}
    assert response.category_id == str(category_id)
    assert response.editable is True


def test_setting_response_exposes_read_only_flag():
    category_id = PydanticObjectId("64a1a1a1a1a1a1a1a1a1a1a1")
    setting = SystemSetting(
        key="dashboard_outages_schedule_region",
        label="Schedule region",
        description="YASNO region ID",
        setting_type="number",
        default_value=0,
        editable=False,
        category_id=category_id,
    )

    assert SettingResponse.from_model(setting).editable is False


def test_settings_grouped_response_contains_category_labels():
    response = SettingsGroupedResponse(
        categories={
            "category-id": CategorySettingsResponse(
                id="category-id",
                label=LocalizableValue({"en": "Buildings", "uk": "Будівлі"}),
                settings=[],
            ),
        },
    )

    assert response.categories["category-id"].label.root == {
        "en": "Buildings",
        "uk": "Будівлі",
    }
