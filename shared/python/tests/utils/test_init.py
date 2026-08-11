"""Tests for shared/utils/__init__.py exports."""
from shared.utils import (
    load_and_register_modules,
    generate_api_token,
    generate_secret_key,
    generate_password_reset_token,
    register_chained_signal_handlers,
)


class TestUtilsExports:
    def test_load_and_register_modules_exported(self):
        assert load_and_register_modules is not None

    def test_generate_api_token_exported(self):
        assert generate_api_token is not None

    def test_generate_secret_key_exported(self):
        assert generate_secret_key is not None

    def test_generate_password_reset_token_exported(self):
        assert generate_password_reset_token is not None

    def test_register_chained_signal_handlers_exported(self):
        assert register_chained_signal_handlers is not None
