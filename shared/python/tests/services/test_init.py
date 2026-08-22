"""Tests for shared/services/__init__.py exports."""
from shared.services import (
    EventsService,
    EventItem,
    EventsServiceConfig,
    TranslationService,
    BaseDeyeClient,
    DeyeCredentials,
)


class TestServiceExports:
    def test_events_service_exported(self):
        assert EventsService is not None

    def test_event_item_exported(self):
        assert EventItem is not None

    def test_events_service_config_exported(self):
        assert EventsServiceConfig is not None

    def test_translation_service_exported(self):
        assert TranslationService is not None

    def test_base_deye_client_exported(self):
        assert BaseDeyeClient is not None

    def test_deye_credentials_exported(self):
        assert DeyeCredentials is not None
