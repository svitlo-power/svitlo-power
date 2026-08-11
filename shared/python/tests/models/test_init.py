"""Tests for shared/models/__init__.py exports."""
from shared.models import (
    BeanieFilter,
    Bot,
    AllowedChat,
    ChatRequest,
    User,
    ReportMode,
    Message,
    Station,
    Building,
    StationData,
    ExtData,
    ExtDevice,
    DashboardConfig,
    StationConnection,
    VisitCounter,
    DailyVisitCounter,
    LookupValue,
    LocalizableValue,
    LoginHistory,
)
from shared.models import BEANIE_MODELS


class TestExports:
    def test_beanie_filter_exported(self):
        assert BeanieFilter is not None

    def test_bot_exported(self):
        assert Bot is not None

    def test_allowed_chat_exported(self):
        assert AllowedChat is not None

    def test_chat_request_exported(self):
        assert ChatRequest is not None

    def test_user_exported(self):
        assert User is not None

    def test_report_mode_exported(self):
        assert ReportMode is not None

    def test_message_exported(self):
        assert Message is not None

    def test_station_exported(self):
        assert Station is not None

    def test_building_exported(self):
        assert Building is not None

    def test_station_data_exported(self):
        assert StationData is not None

    def test_ext_data_exported(self):
        assert ExtData is not None

    def test_ext_device_exported(self):
        assert ExtDevice is not None

    def test_dashboard_config_exported(self):
        assert DashboardConfig is not None

    def test_station_connection_exported(self):
        assert StationConnection is not None

    def test_visit_counter_exported(self):
        assert VisitCounter is not None

    def test_daily_visit_counter_exported(self):
        assert DailyVisitCounter is not None

    def test_lookup_value_exported(self):
        assert LookupValue is not None

    def test_localizable_value_exported(self):
        assert LocalizableValue is not None

    def test_login_history_exported(self):
        assert LoginHistory is not None


class TestBeanieModels:
    def test_beanie_models_is_list(self):
        assert isinstance(BEANIE_MODELS, list)

    def test_beanie_models_contains_bot(self):
        assert Bot in BEANIE_MODELS

    def test_beanie_models_contains_user(self):
        assert User in BEANIE_MODELS

    def test_beanie_models_contains_message(self):
        assert Message in BEANIE_MODELS

    def test_beanie_models_contains_station(self):
        assert Station in BEANIE_MODELS

    def test_beanie_models_contains_building(self):
        assert Building in BEANIE_MODELS

    def test_beanie_models_contains_station_data(self):
        assert StationData in BEANIE_MODELS

    def test_beanie_models_contains_ext_data(self):
        assert ExtData in BEANIE_MODELS

    def test_beanie_models_contains_ext_device(self):
        assert ExtDevice in BEANIE_MODELS

    def test_beanie_models_contains_dashboard_config(self):
        assert DashboardConfig in BEANIE_MODELS

    def test_beanie_models_contains_station_connection(self):
        assert StationConnection in BEANIE_MODELS

    def test_beanie_models_contains_visit_counter(self):
        assert VisitCounter in BEANIE_MODELS

    def test_beanie_models_contains_daily_visit_counter(self):
        assert DailyVisitCounter in BEANIE_MODELS

    def test_beanie_models_contains_login_history(self):
        assert LoginHistory in BEANIE_MODELS

    def test_beanie_models_contains_allowed_chat(self):
        assert AllowedChat in BEANIE_MODELS

    def test_beanie_models_contains_chat_request(self):
        assert ChatRequest in BEANIE_MODELS
