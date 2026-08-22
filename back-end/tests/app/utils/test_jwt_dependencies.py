"""Tests for app/utils/jwt_dependencies.py."""
from datetime import timedelta
from unittest.mock import MagicMock, AsyncMock, patch

import pytest
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from starlette.status import HTTP_401_UNAUTHORIZED, HTTP_403_FORBIDDEN

from app.utils.jwt_dependencies import (
    get_current_jwt,
    jwt_required,
    jwt_refresh_required,
    jwt_reporter_only,
    get_jwt_from_query,
    is_authenticated,
    get_identity,
    get_current_jwt_optional,
)


class TestGetCurrentJwt:
    @pytest.mark.asyncio
    async def test_valid_token_returns_claims(self, mock_settings):
        from shared.utils.jwt_utils import create_access_token

        token = create_access_token(
            identity="testuser",
            expires=timedelta(minutes=30),
            secret_key=mock_settings.JWT_SECRET_KEY,
        )
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)

        with patch("app.utils.jwt_dependencies.Injected", return_value=mock_settings):
            result = get_current_jwt(credentials, mock_settings)
            assert result["sub"] == "testuser"
            assert result["type"] == "access"

    @pytest.mark.asyncio
    async def test_invalid_token_raises_401(self, mock_settings):
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="invalid-token")

        with pytest.raises(HTTPException) as exc_info:
            await get_current_jwt(credentials, mock_settings)

        assert exc_info.value.status_code == HTTP_401_UNAUTHORIZED
        assert "Invalid or expired JWT token" in exc_info.value.detail


class TestJwtRequired:
    @pytest.mark.asyncio
    async def test_reporter_raises_403(self):
        claims = {"sub": "reporter", "is_reporter": True}
        with pytest.raises(HTTPException) as exc_info:
            jwt_required(claims)
        assert exc_info.value.status_code == HTTP_403_FORBIDDEN

    @pytest.mark.asyncio
    async def test_non_reporter_returns_claims(self):
        claims = {"sub": "user", "is_reporter": False}
        result = jwt_required(claims)
        assert result == claims

    @pytest.mark.asyncio
    async def test_no_reporter_flag_returns_claims(self):
        claims = {"sub": "user"}
        result = jwt_required(claims)
        assert result == claims


class TestJwtRefreshRequired:
    @pytest.mark.asyncio
    async def test_access_token_raises_403(self):
        claims = {"sub": "user", "type": "access"}
        with pytest.raises(HTTPException) as exc_info:
            jwt_refresh_required(claims)
        assert exc_info.value.status_code == HTTP_403_FORBIDDEN

    @pytest.mark.asyncio
    async def test_refresh_token_returns_claims(self):
        claims = {"sub": "user", "type": "refresh"}
        result = jwt_refresh_required(claims)
        assert result == claims


class TestJwtReporterOnly:
    @pytest.mark.asyncio
    async def test_non_reporter_raises_403(self):
        claims = {"sub": "user", "is_reporter": False}
        with pytest.raises(HTTPException) as exc_info:
            jwt_reporter_only(claims)
        assert exc_info.value.status_code == HTTP_403_FORBIDDEN

    @pytest.mark.asyncio
    async def test_reporter_returns_claims(self):
        claims = {"sub": "reporter", "is_reporter": True}
        result = jwt_reporter_only(claims)
        assert result == claims


class TestGetJwtFromQuery:
    @pytest.mark.asyncio
    async def test_none_token_returns_none(self, mock_settings):
        result = get_jwt_from_query(None, mock_settings)
        assert result is None

    @pytest.mark.asyncio
    async def test_valid_token_returns_claims(self, mock_settings):
        from shared.utils.jwt_utils import create_access_token

        token = create_access_token(
            identity="testuser",
            expires=timedelta(minutes=30),
            secret_key=mock_settings.JWT_SECRET_KEY,
        )
        result = get_jwt_from_query(token, mock_settings)
        assert result["sub"] == "testuser"

    @pytest.mark.asyncio
    async def test_invalid_token_raises_401(self, mock_settings):
        with pytest.raises(HTTPException) as exc_info:
            await get_jwt_from_query("invalid", mock_settings)
        assert exc_info.value.status_code == HTTP_401_UNAUTHORIZED


class TestIsAuthenticated:
    def test_none_claims_returns_false(self):
        assert is_authenticated(None) is False

    def test_claims_without_sub_returns_false(self):
        assert is_authenticated({"type": "access"}) is False

    def test_claims_with_sub_returns_true(self):
        assert is_authenticated({"sub": "user"}) is True


class TestGetIdentity:
    def test_none_claims_returns_none(self):
        assert get_identity(None) is None

    def test_claims_without_sub_returns_none(self):
        assert get_identity({"type": "access"}) is None

    def test_claims_with_sub_returns_sub(self):
        assert get_identity({"sub": "user"}) == "user"


class TestGetCurrentJwtOptional:
    @pytest.mark.asyncio
    async def test_none_credentials_returns_none(self, mock_settings):
        result = get_current_jwt_optional(None, mock_settings)
        assert result is None

    @pytest.mark.asyncio
    async def test_valid_token_returns_claims(self, mock_settings):
        from shared.utils.jwt_utils import create_access_token

        token = create_access_token(
            identity="testuser",
            expires=timedelta(minutes=30),
            secret_key=mock_settings.JWT_SECRET_KEY,
        )
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=token)
        result = get_current_jwt_optional(credentials, mock_settings)
        assert result["sub"] == "testuser"

    @pytest.mark.asyncio
    async def test_invalid_token_raises_401(self, mock_settings):
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="invalid")
        with pytest.raises(HTTPException) as exc_info:
            await get_current_jwt_optional(credentials, mock_settings)
        assert exc_info.value.status_code == HTTP_401_UNAUTHORIZED
