"""Tests for shared/models/dashboard_config.py."""
from shared.models.dashboard_config import DashboardConfig


class TestDashboardConfig:
    def test_has_title_field(self):
        assert "title" in DashboardConfig.model_fields

    def test_has_enable_outages_schedule_field(self):
        assert "enable_outages_schedule" in DashboardConfig.model_fields

    def test_enable_outages_schedule_defaults_false(self):
        assert DashboardConfig.model_fields["enable_outages_schedule"].default is False

    def test_has_outages_schedule_queue_field(self):
        assert "outages_schedule_queue" in DashboardConfig.model_fields

    def test_outages_schedule_queue_defaults_none(self):
        # Optional[str] without explicit default is required in Pydantic v2
        from pydantic.fields import PydanticUndefined
        assert DashboardConfig.model_fields["outages_schedule_queue"].default is PydanticUndefined

    def test_settings_name(self):
        assert DashboardConfig.Settings.name == "dashboard_config"
