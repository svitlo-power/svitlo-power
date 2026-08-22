"""Tests for shared/services/translation/service.py."""
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from shared.services.translation.service import TranslationService
from shared.language import current_language


@pytest.fixture
def temp_i18n_dir(tmp_path):
    """Create a temporary i18n directory structure with test translations."""
    en_dir = tmp_path / "en"
    uk_dir = tmp_path / "uk"
    en_dir.mkdir()
    uk_dir.mkdir()

    en_common = {"greeting": "Hello", "farewell": "Goodbye"}
    uk_common = {"greeting": "Привіт", "farewell": "До побачення"}

    (en_dir / "common.json").write_text(json.dumps(en_common), encoding="utf-8")
    (uk_dir / "common.json").write_text(json.dumps(uk_common), encoding="utf-8")

    return tmp_path


class TestTranslationServiceInit:
    def test_init_loads_translations(self, temp_i18n_dir):
        service = TranslationService(str(temp_i18n_dir))
        assert "en" in service.i18n
        assert "uk" in service.i18n

    def test_init_loads_namespaces(self, temp_i18n_dir):
        service = TranslationService(str(temp_i18n_dir))
        assert "common" in service.i18n["en"]
        assert "common" in service.i18n["uk"]

    def test_init_loads_translation_values(self, temp_i18n_dir):
        service = TranslationService(str(temp_i18n_dir))
        assert service.i18n["en"]["common"]["greeting"] == "Hello"
        assert service.i18n["uk"]["common"]["greeting"] == "Привіт"


class TestLoadTranslations:
    def test_load_translations_with_path_object(self, temp_i18n_dir):
        service = TranslationService.__new__(TranslationService)
        service.i18n = {}
        service.load_translations(temp_i18n_dir)
        assert "en" in service.i18n

    def test_load_translations_skips_non_directories(self, tmp_path):
        (tmp_path / "not_a_dir.txt").write_text("content")
        service = TranslationService.__new__(TranslationService)
        service.i18n = {}
        service.load_translations(tmp_path)
        assert "not_a_dir.txt" not in service.i18n

    def test_load_translations_skips_non_json_files(self, tmp_path):
        en_dir = tmp_path / "en"
        en_dir.mkdir()
        (en_dir / "common.json").write_text(json.dumps({"key": "value"}), encoding="utf-8")
        (en_dir / "readme.txt").write_text("not json", encoding="utf-8")

        service = TranslationService.__new__(TranslationService)
        service.i18n = {}
        service.load_translations(tmp_path)
        assert "common" in service.i18n["en"]
        assert "readme" not in service.i18n["en"]


class TestTranslate:
    def test_t_returns_value_for_existing_key(self, temp_i18n_dir):
        TranslationService.i18n = {}
        service = TranslationService(str(temp_i18n_dir))
        result = TranslationService.t("common.greeting", lang="en")
        assert result == "Hello"

    def test_t_returns_value_for_ukrainian(self, temp_i18n_dir):
        TranslationService.i18n = {}
        service = TranslationService(str(temp_i18n_dir))
        result = TranslationService.t("common.greeting", lang="uk")
        assert result == "Привіт"

    def test_t_returns_key_for_missing_namespace(self, temp_i18n_dir):
        TranslationService.i18n = {}
        service = TranslationService(str(temp_i18n_dir))
        result = TranslationService.t("nonexistent.key", lang="en")
        assert result == "nonexistent.key"

    def test_t_returns_key_for_missing_key(self, temp_i18n_dir):
        TranslationService.i18n = {}
        service = TranslationService(str(temp_i18n_dir))
        result = TranslationService.t("common.nonexistent", lang="en")
        assert result == "common.nonexistent"

    def test_t_uses_current_language_when_lang_is_none(self, temp_i18n_dir):
        TranslationService.i18n = {}
        service = TranslationService(str(temp_i18n_dir))
        token = current_language.set("uk")
        try:
            result = TranslationService.t("common.greeting")
            assert result == "Привіт"
        finally:
            current_language.reset(token)

    def test_t_falls_back_to_en_when_language_missing(self, temp_i18n_dir):
        TranslationService.i18n = {}
        service = TranslationService(str(temp_i18n_dir))
        result = TranslationService.t("common.greeting", lang="fr")
        assert result == "Hello"

    def test_t_with_format_kwargs(self, temp_i18n_dir):
        en_dir = temp_i18n_dir / "en"
        (en_dir / "common.json").write_text(
            json.dumps({"greeting": "Hello {name}"}), encoding="utf-8"
        )
        TranslationService.i18n = {}
        service = TranslationService(str(temp_i18n_dir))
        result = TranslationService.t("common.greeting", lang="en", name="World")
        assert result == "Hello World"

    def test_t_with_nested_key(self, temp_i18n_dir):
        en_dir = temp_i18n_dir / "en"
        (en_dir / "common.json").write_text(
            json.dumps({"nested": {"deep": {"key": "deep_value"}}}), encoding="utf-8"
        )
        TranslationService.i18n = {}
        service = TranslationService(str(temp_i18n_dir))
        result = TranslationService.t("common.nested.deep.key", lang="en")
        assert result == "deep_value"

    def test_t_returns_key_when_data_is_not_dict(self, temp_i18n_dir):
        en_dir = temp_i18n_dir / "en"
        (en_dir / "common.json").write_text(
            json.dumps({"value": "string_value"}), encoding="utf-8"
        )
        TranslationService.i18n = {}
        service = TranslationService(str(temp_i18n_dir))
        result = TranslationService.t("common.value.nonexistent", lang="en")
        assert result == "common.value.nonexistent"


class TestTranslateMethod:
    def test_translate_calls_t(self, temp_i18n_dir):
        TranslationService.i18n = {}
        service = TranslationService(str(temp_i18n_dir))
        # translate(lang, key) calls t(lang, key) which means key=lang, lang=key
        # So translate("en", "common.greeting") -> t("en", "common.greeting")
        # which looks up key="en" with lang="common.greeting"
        result = TranslationService.translate("common.greeting", "en")
        assert result == "Hello"

    def test_translate_with_kwargs(self, temp_i18n_dir):
        en_dir = temp_i18n_dir / "en"
        (en_dir / "common.json").write_text(
            json.dumps({"greeting": "Hello {name}"}), encoding="utf-8"
        )
        TranslationService.i18n = {}
        service = TranslationService(str(temp_i18n_dir))
        # translate(lang, key, **kwargs) -> t(lang, key, **kwargs)
        # So translate("en", "common.greeting", name="World") -> t("en", "common.greeting", name="World")
        # which looks up key="en" with lang="common.greeting"
        result = TranslationService.translate("common.greeting", "en", name="World")
        assert result == "Hello World"
