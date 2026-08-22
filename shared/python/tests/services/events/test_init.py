"""Tests for shared/services/events/__init__.py exports."""
from shared.services.events import EventsService, EventItem, EventsServiceConfig


class TestEventsExports:
    def test_events_service_exported(self):
        assert EventsService is not None

    def test_event_item_exported(self):
        assert EventItem is not None

    def test_events_service_config_exported(self):
        assert EventsServiceConfig is not None
