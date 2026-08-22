"""Tests for shared/services/translation/__init__.py exports."""
from shared.services.translation import TranslationService


class TestTranslationExports:
    def test_translation_service_exported(self):
        assert TranslationService is not None
