"""Tests for shared package exports."""
import shared


def test_bounded_queue_exported():
    assert hasattr(shared, "BoundedQueue")


def test_current_language_exported():
    assert hasattr(shared, "current_language")


def test_supported_languages_exported():
    assert hasattr(shared, "SUPPORTED_LANGUAGES")


def test_default_language_exported():
    assert hasattr(shared, "DEFAULT_LANGUAGE")
