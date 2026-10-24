from beanie import PydanticObjectId

from app.models.api.settings import (
    CategorySettingsResponse,
    SettingResponse,
    SettingsGroupedResponse,
)
from shared.models.localizable_value import LocalizableValue
from shared.models.system_setting import SystemSetting

from app.models.api.settings import SettingUpdateRequest


def test_setting_update_request_accepts_localizable_text():
    request = SettingUpdateRequest(value={"en": "Dashboard", "uk": "Панель"})

    assert isinstance(request.value, LocalizableValue)
    assert request.value.root == {"en": "Dashboard", "uk": "Панель"}


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
