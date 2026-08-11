"""Tests for shared/models/visit_counter.py."""
from shared.models.visit_counter import VisitCounter, DailyVisitCounter


class TestVisitCounter:
    def test_has_visits_count_field(self):
        assert "visits_count" in VisitCounter.model_fields

    def test_visits_count_defaults_zero(self):
        assert VisitCounter.model_fields["visits_count"].default == 0

    def test_settings_name(self):
        assert VisitCounter.Settings.name == "visit_counters"


class TestDailyVisitCounter:
    def test_has_visits_count_field(self):
        assert "visits_count" in DailyVisitCounter.model_fields

    def test_visits_count_defaults_zero(self):
        assert DailyVisitCounter.model_fields["visits_count"].default == 0

    def test_has_date_field(self):
        assert "date" in DailyVisitCounter.model_fields

    def test_settings_name(self):
        assert DailyVisitCounter.Settings.name == "daily_visit_counters"
