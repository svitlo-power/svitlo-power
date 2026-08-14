"""Tests for app/services/authorization/service.py."""
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import jwt

from app.services.authorization.service import AuthorizationService
from shared.models.user import User, ReportMode


class TestAuthorizationServiceInit:
    def test_init_stores_dependencies(self):
        mock_users_repo = MagicMock()
        mock_login_history_repo = MagicMock()
        mock_settings = MagicMock()
        mock_settings.JWT_SECRET_KEY = "test-secret"
        mock_settings.JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=60)
        mock_settings.JWT_REFRESH_TOKEN_EXPIRES = timedelta(minutes=60 * 24 * 7)

        service = AuthorizationService(mock_users_repo, mock_login_history_repo, mock_settings)
        assert service._users_repository is mock_users_repo
        assert service._login_history_repository is mock_login_history_repo
        assert service._settings is mock_settings


class TestAuthorizationServiceGetCurrentUser:
    @pytest.mark.asyncio
    async def test_valid_token_returns_username(self):
        mock_users_repo = MagicMock()
        mock_login_history_repo = MagicMock()
        mock_settings = MagicMock()
        mock_settings.JWT_SECRET_KEY = "test-secret"
        mock_settings.JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=60)
        mock_settings.JWT_REFRESH_TOKEN_EXPIRES = timedelta(minutes=60 * 24 * 7)

        service = AuthorizationService(mock_users_repo, mock_login_history_repo, mock_settings)

        token = jwt.encode(
            {"sub": "testuser", "type": "access"},
            "test-secret",
            algorithm="HS256",
        )

        result = await service.get_current_user(token)
        assert result == "testuser"

    @pytest.mark.asyncio
    async def test_invalid_token_raises_http_exception(self):
        mock_users_repo = MagicMock()
        mock_login_history_repo = MagicMock()
        mock_settings = MagicMock()
        mock_settings.JWT_SECRET_KEY = "test-secret"
        mock_settings.JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=60)
        mock_settings.JWT_REFRESH_TOKEN_EXPIRES = timedelta(minutes=60 * 24 * 7)

        service = AuthorizationService(mock_users_repo, mock_login_history_repo, mock_settings)

        with pytest.raises(HTTPException) as exc_info:
            await service.get_current_user("invalid-token")

        assert exc_info.value.status_code == 401


class TestAuthorizationServiceLogin:
    @pytest.mark.asyncio
    async def test_login_success(self):
        mock_users_repo = MagicMock()
        mock_login_history_repo = MagicMock()
        mock_login_history_repo.add_login_history = AsyncMock()
        mock_settings = MagicMock()
        mock_settings.JWT_SECRET_KEY = "test-secret"
        mock_settings.JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=60)
        mock_settings.JWT_REFRESH_TOKEN_EXPIRES = timedelta(minutes=60 * 24 * 7)

        user = User(name="testuser", password="hashed_password", is_reporter=False)
        mock_users_repo.get_user = AsyncMock(return_value=user)

        service = AuthorizationService(mock_users_repo, mock_login_history_repo, mock_settings)

        with patch("app.services.authorization.service.pwd_context.verify", return_value=True):
            access, refresh = await service.login("testuser", "password", "127.0.0.1")

        assert access is not None
        assert refresh is not None
        mock_login_history_repo.add_login_history.assert_called_once()

    @pytest.mark.asyncio
    async def test_login_user_not_found(self):
        mock_users_repo = MagicMock()
        mock_login_history_repo = MagicMock()
        mock_settings = MagicMock()
        mock_settings.JWT_SECRET_KEY = "test-secret"
        mock_settings.JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=60)
        mock_settings.JWT_REFRESH_TOKEN_EXPIRES = timedelta(minutes=60 * 24 * 7)

        mock_users_repo.get_user = AsyncMock(return_value=None)

        service = AuthorizationService(mock_users_repo, mock_login_history_repo, mock_settings)

        with pytest.raises(ValueError, match="invalidLoginOrPassword"):
            await service.login("nonexistent", "password", "127.0.0.1")

    @pytest.mark.asyncio
    async def test_login_reporter_not_allowed(self):
        mock_users_repo = MagicMock()
        mock_login_history_repo = MagicMock()
        mock_settings = MagicMock()
        mock_settings.JWT_SECRET_KEY = "test-secret"
        mock_settings.JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=60)
        mock_settings.JWT_REFRESH_TOKEN_EXPIRES = timedelta(minutes=60 * 24 * 7)

        user = User(name="reporter", password="hashed", is_reporter=True, report_mode=ReportMode.EVENT)
        mock_users_repo.get_user = AsyncMock(return_value=user)

        service = AuthorizationService(mock_users_repo, mock_login_history_repo, mock_settings)

        with pytest.raises(ValueError, match="invalidLoginOrPassword"):
            await service.login("reporter", "password", "127.0.0.1")

    @pytest.mark.asyncio
    async def test_login_wrong_password(self):
        mock_users_repo = MagicMock()
        mock_login_history_repo = MagicMock()
        mock_settings = MagicMock()
        mock_settings.JWT_SECRET_KEY = "test-secret"
        mock_settings.JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=60)
        mock_settings.JWT_REFRESH_TOKEN_EXPIRES = timedelta(minutes=60 * 24 * 7)

        user = User(name="testuser", password="hashed_password", is_reporter=False)
        mock_users_repo.get_user = AsyncMock(return_value=user)

        service = AuthorizationService(mock_users_repo, mock_login_history_repo, mock_settings)

        with patch("app.services.authorization.service.pwd_context.verify", return_value=False):
            with pytest.raises(ValueError, match="invalidLoginOrPassword"):
                await service.login("testuser", "wrong", "127.0.0.1")


class TestAuthorizationServiceGetUser:
    @pytest.mark.asyncio
    async def test_get_user_returns_user(self):
        mock_users_repo = MagicMock()
        mock_login_history_repo = MagicMock()
        mock_settings = MagicMock()
        mock_settings.JWT_SECRET_KEY = "test-secret"
        mock_settings.JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=60)
        mock_settings.JWT_REFRESH_TOKEN_EXPIRES = timedelta(minutes=60 * 24 * 7)

        user = User(name="testuser", password="hashed", is_reporter=False)
        mock_users_repo.get_user = AsyncMock(return_value=user)

        service = AuthorizationService(mock_users_repo, mock_login_history_repo, mock_settings)
        result = await service.get_user("testuser")
        assert result == user


class TestAuthorizationServiceRefreshToken:
    @pytest.mark.asyncio
    async def test_refresh_token_success(self):
        mock_users_repo = MagicMock()
        mock_login_history_repo = MagicMock()
        mock_settings = MagicMock()
        mock_settings.JWT_SECRET_KEY = "test-secret"
        mock_settings.JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=60)
        mock_settings.JWT_REFRESH_TOKEN_EXPIRES = timedelta(minutes=60 * 24 * 7)

        user = User(name="testuser", password="hashed", is_reporter=False)
        mock_users_repo.get_user = AsyncMock(return_value=user)

        service = AuthorizationService(mock_users_repo, mock_login_history_repo, mock_settings)
        result = await service.refresh_token("testuser")
        assert result is not None

    @pytest.mark.asyncio
    async def test_refresh_token_user_not_found(self):
        mock_users_repo = MagicMock()
        mock_login_history_repo = MagicMock()
        mock_settings = MagicMock()
        mock_settings.JWT_SECRET_KEY = "test-secret"
        mock_settings.JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=60)
        mock_settings.JWT_REFRESH_TOKEN_EXPIRES = timedelta(minutes=60 * 24 * 7)

        mock_users_repo.get_user = AsyncMock(return_value=None)

        service = AuthorizationService(mock_users_repo, mock_login_history_repo, mock_settings)
        with pytest.raises(ValueError, match="userNotFound"):
            await service.refresh_token("nonexistent")

    @pytest.mark.asyncio
    async def test_refresh_token_reporter_not_allowed(self):
        mock_users_repo = MagicMock()
        mock_login_history_repo = MagicMock()
        mock_settings = MagicMock()
        mock_settings.JWT_SECRET_KEY = "test-secret"
        mock_settings.JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=60)
        mock_settings.JWT_REFRESH_TOKEN_EXPIRES = timedelta(minutes=60 * 24 * 7)

        user = User(name="reporter", password="hashed", is_reporter=True, report_mode=ReportMode.EVENT)
        mock_users_repo.get_user = AsyncMock(return_value=user)

        service = AuthorizationService(mock_users_repo, mock_login_history_repo, mock_settings)
        with pytest.raises(ValueError, match="userCannotLogIn"):
            await service.refresh_token("reporter")


class TestAuthorizationServiceStartChangePassword:
    @pytest.mark.asyncio
    async def test_start_change_password_success(self):
        mock_users_repo = MagicMock()
        mock_login_history_repo = MagicMock()
        mock_settings = MagicMock()
        mock_settings.JWT_SECRET_KEY = "test-secret"
        mock_settings.JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=60)
        mock_settings.JWT_REFRESH_TOKEN_EXPIRES = timedelta(minutes=60 * 24 * 7)

        user = User(name="testuser", password="hashed", is_reporter=False)
        mock_users_repo.get_user = AsyncMock(return_value=user)
        mock_users_repo.set_password_reset_token = AsyncMock()

        service = AuthorizationService(mock_users_repo, mock_login_history_repo, mock_settings)
        token = await service.start_change_password("testuser", hours=2)
        assert token is not None
        mock_users_repo.set_password_reset_token.assert_called_once()

    @pytest.mark.asyncio
    async def test_start_change_password_user_not_found(self):
        mock_users_repo = MagicMock()
        mock_login_history_repo = MagicMock()
        mock_settings = MagicMock()
        mock_settings.JWT_SECRET_KEY = "test-secret"
        mock_settings.JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=60)
        mock_settings.JWT_REFRESH_TOKEN_EXPIRES = timedelta(minutes=60 * 24 * 7)

        mock_users_repo.get_user = AsyncMock(return_value=None)

        service = AuthorizationService(mock_users_repo, mock_login_history_repo, mock_settings)
        with pytest.raises(ValueError, match="userNotFound"):
            await service.start_change_password("nonexistent", hours=2)


class TestAuthorizationServiceCancelChangePassword:
    @pytest.mark.asyncio
    async def test_cancel_change_password_success(self):
        mock_users_repo = MagicMock()
        mock_login_history_repo = MagicMock()
        mock_settings = MagicMock()
        mock_settings.JWT_SECRET_KEY = "test-secret"
        mock_settings.JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=60)
        mock_settings.JWT_REFRESH_TOKEN_EXPIRES = timedelta(minutes=60 * 24 * 7)

        user = User(name="testuser", password="hashed", is_reporter=False)
        mock_users_repo.get_user = AsyncMock(return_value=user)
        mock_users_repo.remove_password_reset_token = AsyncMock()

        service = AuthorizationService(mock_users_repo, mock_login_history_repo, mock_settings)
        await service.cancel_change_password("testuser")
        mock_users_repo.remove_password_reset_token.assert_called_once_with(user.id)

    @pytest.mark.asyncio
    async def test_cancel_change_password_user_not_found(self):
        mock_users_repo = MagicMock()
        mock_login_history_repo = MagicMock()
        mock_settings = MagicMock()
        mock_settings.JWT_SECRET_KEY = "test-secret"
        mock_settings.JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=60)
        mock_settings.JWT_REFRESH_TOKEN_EXPIRES = timedelta(minutes=60 * 24 * 7)

        mock_users_repo.get_user = AsyncMock(return_value=None)

        service = AuthorizationService(mock_users_repo, mock_login_history_repo, mock_settings)
        with pytest.raises(ValueError, match="userNotFound"):
            await service.cancel_change_password("nonexistent")


class TestAuthorizationServiceChangePassword:
    @pytest.mark.asyncio
    async def test_change_password_success(self):
        mock_users_repo = MagicMock()
        mock_login_history_repo = MagicMock()
        mock_settings = MagicMock()
        mock_settings.JWT_SECRET_KEY = "test-secret"
        mock_settings.JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=60)
        mock_settings.JWT_REFRESH_TOKEN_EXPIRES = timedelta(minutes=60 * 24 * 7)

        user = User(
            name="testuser",
            password="hashed",
            is_reporter=False,
            password_reset_token="reset-token",
            reset_token_expiration=datetime.now(timezone.utc) + timedelta(hours=1),
        )
        mock_users_repo.get_user_by_reset_token = AsyncMock(return_value=user)
        mock_users_repo.change_password = AsyncMock()

        service = AuthorizationService(mock_users_repo, mock_login_history_repo, mock_settings)
        await service.change_password("reset-token", "new-password")
        mock_users_repo.change_password.assert_called_once()

    @pytest.mark.asyncio
    async def test_change_password_user_not_found(self):
        mock_users_repo = MagicMock()
        mock_login_history_repo = MagicMock()
        mock_settings = MagicMock()
        mock_settings.JWT_SECRET_KEY = "test-secret"
        mock_settings.JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=60)
        mock_settings.JWT_REFRESH_TOKEN_EXPIRES = timedelta(minutes=60 * 24 * 7)

        mock_users_repo.get_user_by_reset_token = AsyncMock(return_value=None)

        service = AuthorizationService(mock_users_repo, mock_login_history_repo, mock_settings)
        with pytest.raises(ValueError, match="userNotFound"):
            await service.change_password("invalid-token", "new-password")

    @pytest.mark.asyncio
    async def test_change_password_expired_token(self):
        mock_users_repo = MagicMock()
        mock_login_history_repo = MagicMock()
        mock_settings = MagicMock()
        mock_settings.JWT_SECRET_KEY = "test-secret"
        mock_settings.JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=60)
        mock_settings.JWT_REFRESH_TOKEN_EXPIRES = timedelta(minutes=60 * 24 * 7)

        user = User(
            name="testuser",
            password="hashed",
            is_reporter=False,
            password_reset_token="reset-token",
            reset_token_expiration=datetime.now(timezone.utc) - timedelta(hours=1),
        )
        mock_users_repo.get_user_by_reset_token = AsyncMock(return_value=user)
        mock_users_repo.remove_password_reset_token = AsyncMock()

        service = AuthorizationService(mock_users_repo, mock_login_history_repo, mock_settings)
        with pytest.raises(ValueError, match="invalidToken"):
            await service.change_password("reset-token", "new-password")


class TestAuthorizationServiceAddUser:
    @pytest.mark.asyncio
    async def test_add_user_success(self):
        mock_users_repo = MagicMock()
        mock_login_history_repo = MagicMock()
        mock_settings = MagicMock()
        mock_settings.JWT_SECRET_KEY = "test-secret"
        mock_settings.JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=60)
        mock_settings.JWT_REFRESH_TOKEN_EXPIRES = timedelta(minutes=60 * 24 * 7)

        mock_users_repo.force_create_user = AsyncMock()

        service = AuthorizationService(mock_users_repo, mock_login_history_repo, mock_settings)
        await service.add_user("admin", "password123")
        mock_users_repo.force_create_user.assert_called_once()
        call_args = mock_users_repo.force_create_user.call_args
        assert call_args[0][0] == "admin"
        assert call_args[0][1] != "password123"  # Should be hashed


class TestAuthorizationServiceRenameUser:
    @pytest.mark.asyncio
    async def test_rename_user_delegates_to_repository(self):
        mock_users_repo = MagicMock()
        mock_login_history_repo = MagicMock()
        mock_settings = MagicMock()
        mock_settings.JWT_SECRET_KEY = "test-secret"
        mock_settings.JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=60)
        mock_settings.JWT_REFRESH_TOKEN_EXPIRES = timedelta(minutes=60 * 24 * 7)

        mock_users_repo.rename_user = AsyncMock()

        service = AuthorizationService(mock_users_repo, mock_login_history_repo, mock_settings)
        await service.rename_user(123, "new_name")
        mock_users_repo.rename_user.assert_called_once_with(123, "new_name")
