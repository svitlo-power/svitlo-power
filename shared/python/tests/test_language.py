"""Tests for shared/language.py."""
from contextvars import ContextVar

from shared.language import SUPPORTED_LANGUAGES, DEFAULT_LANGUAGE, current_language


class TestSupportedLanguages:
    def test_supported_languages_is_set(self):
        assert isinstance(SUPPORTED_LANGUAGES, set)

    def test_contains_english(self):
        assert "en" in SUPPORTED_LANGUAGES

    def test_contains_ukrainian(self):
        assert "uk" in SUPPORTED_LANGUAGES

    def test_has_two_languages(self):
        assert len(SUPPORTED_LANGUAGES) == 2


class TestDefaultLanguage:
    def test_default_language_is_en(self):
        assert DEFAULT_LANGUAGE == "en"


class TestCurrentLanguage:
    def test_current_language_is_context_var(self):
        assert isinstance(current_language, ContextVar)

    def test_default_value_is_en(self):
        assert current_language.get() == "en"

    def test_can_set_language(self):
        token = current_language.set("uk")
        try:
            assert current_language.get() == "uk"
        finally:
            current_language.reset(token)

    def test_reset_restores_default(self):
        token = current_language.set("uk")
        current_language.reset(token)
        assert current_language.get() == "en"
