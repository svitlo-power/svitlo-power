"""Tests for shared/services/deye_api/__init__.py exports."""
from shared.services.deye_api import BaseDeyeClient, DeyeCredentials


class TestDeyeApiExports:
    def test_base_deye_client_exported(self):
        assert BaseDeyeClient is not None

    def test_deye_credentials_exported(self):
        assert DeyeCredentials is not None
