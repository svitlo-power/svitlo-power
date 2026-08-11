"""Tests for shared/models/localizable_value.py."""
import pytest
from pydantic import ValidationError

from shared.models.localizable_value import LocalizableValue
from shared.language import SUPPORTED_LANGUAGES


class TestLocalizableValueCreation:
    def test_create_with_valid_languages(self):
        lv = LocalizableValue.model_validate({"en": "Hello", "uk": "Привіт"})
        assert lv.root == {"en": "Hello", "uk": "Привіт"}

    def test_create_with_single_language(self):
        lv = LocalizableValue.model_validate({"en": "Hello"})
        assert lv.root == {"en": "Hello"}

    def test_create_with_empty_dict(self):
        lv = LocalizableValue.model_validate({})
        assert lv.root == {}


class TestLocalizableValueValidation:
    def test_invalid_language_key_raises_error(self):
        with pytest.raises(ValidationError) as exc_info:
            LocalizableValue.model_validate({"fr": "Bonjour"})
        assert "Invalid culture code" in str(exc_info.value)

    def test_invalid_language_key_in_multiple_keys(self):
        with pytest.raises(ValidationError):
            LocalizableValue.model_validate({"en": "Hello", "de": "Hallo"})

    def test_valid_language_keys_pass(self):
        lv = LocalizableValue.model_validate({"en": "Hello", "uk": "Привіт"})
        assert lv.root["en"] == "Hello"
        assert lv.root["uk"] == "Привіт"


class TestGetCultureValue:
    def test_get_existing_culture(self):
        lv = LocalizableValue.model_validate({"en": "Hello", "uk": "Привіт"})
        assert lv.get_culture_value("en") == "Hello"
        assert lv.get_culture_value("uk") == "Привіт"

    def test_get_missing_culture_raises_error(self):
        lv = LocalizableValue.model_validate({"en": "Hello"})
        with pytest.raises(ValueError, match="No value found for culture"):
            lv.get_culture_value("uk")

    def test_get_invalid_culture_raises_error(self):
        lv = LocalizableValue.model_validate({"en": "Hello"})
        with pytest.raises(ValueError, match="Invalid culture code"):
            lv.get_culture_value("fr")

    def test_get_culture_with_empty_root(self):
        lv = LocalizableValue.model_validate({})
        with pytest.raises(ValueError, match="No value found for culture"):
            lv.get_culture_value("en")
