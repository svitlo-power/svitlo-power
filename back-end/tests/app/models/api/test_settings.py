from shared.models.localizable_value import LocalizableValue

from app.models.api.settings import SettingUpdateRequest


def test_setting_update_request_accepts_localizable_text():
    request = SettingUpdateRequest(value={"en": "Dashboard", "uk": "Панель"})

    assert isinstance(request.value, LocalizableValue)
    assert request.value.root == {"en": "Dashboard", "uk": "Панель"}
