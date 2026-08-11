"""Tests for shared/utils/jwt_utils.py."""
from datetime import datetime, timedelta, timezone

import pytest
from jose import jwt

from shared.utils.jwt_utils import (
    ALGORITHM,
    InvalidTokenError,
    decode_jwt,
    ensure_access_token,
    ensure_refresh_token,
    ensure_not_reporter,
    create_access_token,
    create_refresh_token,
)


class TestInvalidTokenError:
    def test_is_exception(self):
        assert issubclass(InvalidTokenError, Exception)


class TestDecodeJwt:
    def test_decode_valid_token(self):
        secret = "test_secret"
        payload = {"sub": "user1", "type": "access"}
        token = jwt.encode(payload, secret, algorithm=ALGORITHM)
        decoded = decode_jwt(token, secret)
        assert decoded["sub"] == "user1"
        assert decoded["type"] == "access"

    def test_decode_invalid_token_raises_error(self):
        with pytest.raises(InvalidTokenError):
            decode_jwt("invalid.token.here", "test_secret")

    def test_decode_with_wrong_secret_raises_error(self):
        secret = "test_secret"
        token = jwt.encode({"sub": "user1"}, "wrong_secret", algorithm=ALGORITHM)
        with pytest.raises(InvalidTokenError):
            decode_jwt(token, secret)


class TestEnsureAccessToken:
    def test_valid_access_token(self):
        payload = {"type": "access"}
        ensure_access_token(payload)

    def test_refresh_token_raises_error(self):
        payload = {"type": "refresh"}
        with pytest.raises(InvalidTokenError, match="Access token required"):
            ensure_access_token(payload)

    def test_missing_type_raises_error(self):
        payload = {}
        with pytest.raises(InvalidTokenError, match="Access token required"):
            ensure_access_token(payload)


class TestEnsureRefreshToken:
    def test_valid_refresh_token(self):
        payload = {"type": "refresh"}
        ensure_refresh_token(payload)

    def test_access_token_raises_error(self):
        payload = {"type": "access"}
        with pytest.raises(InvalidTokenError, match="Refresh token required"):
            ensure_refresh_token(payload)

    def test_missing_type_raises_error(self):
        payload = {}
        with pytest.raises(InvalidTokenError, match="Refresh token required"):
            ensure_refresh_token(payload)


class TestEnsureNotReporter:
    def test_non_reporter_passes(self):
        payload = {"is_reporter": False}
        ensure_not_reporter(payload)

    def test_no_reporter_flag_passes(self):
        payload = {}
        ensure_not_reporter(payload)

    def test_reporter_raises_error(self):
        payload = {"is_reporter": True}
        with pytest.raises(InvalidTokenError, match="Reporter token not allowed"):
            ensure_not_reporter(payload)


class TestCreateAccessToken:
    def test_create_access_token(self):
        secret = "test_secret"
        token = create_access_token(
            identity="user1",
            expires=timedelta(minutes=60),
            secret_key=secret,
        )
        decoded = jwt.decode(token, secret, algorithms=[ALGORITHM])
        assert decoded["sub"] == "user1"
        assert decoded["type"] == "access"
        assert "iat" in decoded
        assert "exp" in decoded

    def test_create_access_token_with_additional_claims(self):
        secret = "test_secret"
        token = create_access_token(
            identity="user1",
            expires=timedelta(minutes=60),
            secret_key=secret,
            additional_claims={"is_reporter": True},
        )
        decoded = jwt.decode(token, secret, algorithms=[ALGORITHM])
        assert decoded["is_reporter"] is True

    def test_create_access_token_without_expiration(self):
        secret = "test_secret"
        token = create_access_token(
            identity="user1",
            expires=None,
            secret_key=secret,
        )
        decoded = jwt.decode(token, secret, algorithms=[ALGORITHM])
        assert "exp" not in decoded

    def test_access_token_expiration_correct(self):
        secret = "test_secret"
        expires = timedelta(minutes=30)
        token = create_access_token(
            identity="user1",
            expires=expires,
            secret_key=secret,
        )
        decoded = jwt.decode(token, secret, algorithms=[ALGORITHM])
        now = datetime.now(timezone.utc)
        exp = datetime.fromtimestamp(decoded["exp"], tz=timezone.utc)
        delta = exp - now
        assert 29 <= delta.total_seconds() / 60 <= 30


class TestCreateRefreshToken:
    def test_create_refresh_token(self):
        secret = "test_secret"
        token = create_refresh_token(
            identity="user1",
            expires=timedelta(minutes=60 * 24 * 7),
            secret_key=secret,
        )
        decoded = jwt.decode(token, secret, algorithms=[ALGORITHM])
        assert decoded["sub"] == "user1"
        assert decoded["type"] == "refresh"
        assert "iat" in decoded
        assert "exp" in decoded

    def test_refresh_token_has_expiration(self):
        secret = "test_secret"
        expires = timedelta(minutes=60 * 24 * 7)
        token = create_refresh_token(
            identity="user1",
            expires=expires,
            secret_key=secret,
        )
        decoded = jwt.decode(token, secret, algorithms=[ALGORITHM])
        now = datetime.now(timezone.utc)
        exp = datetime.fromtimestamp(decoded["exp"], tz=timezone.utc)
        delta = exp - now
        assert 60 * 24 * 7 - 1 <= delta.total_seconds() / 60 <= 60 * 24 * 7
