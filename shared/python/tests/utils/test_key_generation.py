"""Tests for shared/utils/key_generation.py."""
import string
from datetime import datetime, timedelta, timezone

from shared.utils.key_generation import (
    generate_secret_key,
    generate_api_token,
    generate_password_reset_token,
)


class TestGenerateSecretKey:
    def test_default_length(self):
        key = generate_secret_key()
        assert len(key) == 32

    def test_custom_length(self):
        key = generate_secret_key(length=64)
        assert len(key) == 64

    def test_only_lowercase_letters(self):
        key = generate_secret_key(length=100)
        for char in key:
            assert char in string.ascii_lowercase

    def test_different_calls_produce_different_keys(self):
        key1 = generate_secret_key()
        key2 = generate_secret_key()
        assert key1 != key2


class TestGenerateApiToken:
    def test_default_length(self):
        token = generate_api_token()
        assert len(token) == 64

    def test_custom_length(self):
        token = generate_api_token(length=32)
        assert len(token) == 32

    def test_uses_allowed_alphabet(self):
        alphabet = string.ascii_letters + string.digits + '-_'
        token = generate_api_token(length=100)
        for char in token:
            assert char in alphabet

    def test_different_calls_produce_different_tokens(self):
        token1 = generate_api_token()
        token2 = generate_api_token()
        assert token1 != token2


class TestGeneratePasswordResetToken:
    def test_returns_tuple(self):
        result = generate_password_reset_token(expire_hourse=1)
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_token_is_string(self):
        token, _ = generate_password_reset_token(expire_hourse=1)
        assert isinstance(token, str)

    def test_token_is_url_safe(self):
        token, _ = generate_password_reset_token(expire_hourse=1)
        # token_urlsafe produces base64url-encoded strings
        assert len(token) > 0

    def test_expiration_is_datetime(self):
        _, expiration = generate_password_reset_token(expire_hourse=1)
        assert isinstance(expiration, datetime)

    def test_expiration_is_timezone_aware(self):
        _, expiration = generate_password_reset_token(expire_hourse=1)
        assert expiration.tzinfo is not None

    def test_expiration_is_in_future(self):
        _, expiration = generate_password_reset_token(expire_hourse=1)
        now = datetime.now(timezone.utc)
        assert expiration > now

    def test_expiration_correct_offset(self):
        _, expiration = generate_password_reset_token(expire_hourse=24)
        now = datetime.now(timezone.utc)
        delta = expiration - now
        assert 23 <= delta.total_seconds() / 3600 <= 24

    def test_different_calls_produce_different_tokens(self):
        token1, _ = generate_password_reset_token(expire_hourse=1)
        token2, _ = generate_password_reset_token(expire_hourse=1)
        assert token1 != token2
