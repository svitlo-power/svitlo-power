"""Tests for shared/models/dashboard_config.py."""
import pytest
from pydantic import ValidationError

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
        assert DashboardConfig.model_fields["outages_schedule_queue"].default is None

    def test_nested_outages_schedule_defaults_none(self):
        assert DashboardConfig.model_fields["outages_schedule"].default is None

    def test_legacy_config_is_migrated(self):
        config = DashboardConfig.model_validate({
            "title": {"en": "Dashboard"},
            "enable_outages_schedule": True,
            "outages_schedule_queue": "1.1",
        })

        assert config.outages_schedule.enable is True
        assert config.outages_schedule.region == "Kyiv"
        assert config.outages_schedule.dso == "Yasno"
        assert config.outages_schedule.queue == "1.1"

    def test_legacy_disabled_config_is_migrated(self):
        config = DashboardConfig.model_validate({
            "title": {"en": "Dashboard"},
            "enable_outages_schedule": False,
            "outages_schedule_queue": None,
        })

        assert config.outages_schedule.enable is False
        assert config.outages_schedule.region is None
        assert config.outages_schedule.dso is None
        assert config.outages_schedule.queue is None

    def test_nested_config_is_preserved(self):
        config = DashboardConfig.model_validate({
            "title": {"en": "Dashboard"},
            "outages_schedule": {
                "enable": True,
                "region": "Lviv",
                "dso": "Lviv DSO",
                "queue": "2.1",
            },
        })

        assert config.outages_schedule.region == "Lviv"
        assert config.outages_schedule.dso == "Lviv DSO"
        assert config.outages_schedule.queue == "2.1"

    @pytest.mark.parametrize(
        "config",
        [
            {"enable": True},
            {"enable": True, "region": " ", "dso": "DSO", "queue": "1.1"},
            {"enable": True, "region": "Kyiv", "dso": " ", "queue": "1.1"},
            {"enable": True, "region": "Kyiv", "dso": "Yasno", "queue": " "},
        ],
    )
    def test_enabled_nested_config_requires_nonblank_selections(self, config):
        with pytest.raises(ValidationError, match="requires region, DSO, and queue"):
            DashboardConfig.model_validate({
                "title": {"en": "Dashboard"},
                "outages_schedule": config,
            })

    def test_non_mapping_input_is_not_migrated(self):
        with pytest.raises(ValidationError):
            DashboardConfig.model_validate("not a mapping")

    def test_settings_name(self):
        assert DashboardConfig.Settings.name == "dashboard_config"
