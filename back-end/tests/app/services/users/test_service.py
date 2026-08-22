"""Tests for app/services/users/service.py."""
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from beanie import PydanticObjectId

from app.services.users.service import UsersService
from app.models.api import UserListResponseModel, LoginHistoryItemResponse
from shared.models.user import User, ReportMode
from shared.models.login_history import LoginHistory


class TestUsersServiceInit:
    def test_init_stores_dependencies(self):
        mock_settings = MagicMock()
        mock_events = MagicMock()
        mock_users_repo = MagicMock()
        mock_login_history_repo = MagicMock()

        service = UsersService(mock_settings, mock_events, mock_users_repo, mock_login_history_repo)
        assert service._settings is mock_settings
        assert service._users_repository is mock_users_repo
        assert service._login_history_repository is mock_login_history_repo


class TestUsersServiceProcessUser:
    def test_process_user_returns_response_model(self):
        mock_settings = MagicMock()
        mock_events = MagicMock()
        mock_users_repo = MagicMock()
        mock_login_history_repo = MagicMock()

        service = UsersService(mock_settings, mock_events, mock_users_repo, mock_login_history_repo)

        user = User(name="testuser", password="hashed", is_active=True, is_reporter=False)
        result = service._process_user(user)
        assert isinstance(result, UserListResponseModel)
        assert result.name == "testuser"
        assert result.is_active is True
        assert result.is_reporter is False

    def test_process_user_with_reporter(self):
        mock_settings = MagicMock()
        mock_events = MagicMock()
        mock_users_repo = MagicMock()
        mock_login_history_repo = MagicMock()

        service = UsersService(mock_settings, mock_events, mock_users_repo, mock_login_history_repo)

        user = User(name="reporter", password="hashed", is_reporter=True, report_mode=ReportMode.EVENT)
        result = service._process_user(user)
        assert result.is_reporter is True
        assert result.report_mode == ReportMode.EVENT


class TestUsersServiceGetUser:
    @pytest.mark.asyncio
    async def test_get_user_returns_processed_user(self):
        mock_settings = MagicMock()
        mock_events = MagicMock()
        mock_users_repo = MagicMock()
        mock_login_history_repo = MagicMock()

        user = User(name="testuser", password="hashed", is_active=True, is_reporter=False)
        mock_users_repo.get_user = AsyncMock(return_value=user)

        service = UsersService(mock_settings, mock_events, mock_users_repo, mock_login_history_repo)
        result = await service.get_user("testuser")
        assert isinstance(result, UserListResponseModel)
        assert result.name == "testuser"


class TestUsersServiceGetUsers:
    @pytest.mark.asyncio
    async def test_get_users_returns_list(self):
        mock_settings = MagicMock()
        mock_events = MagicMock()
        mock_users_repo = MagicMock()
        mock_login_history_repo = MagicMock()

        users = [
            User(name="user1", password="hashed", is_active=True, is_reporter=False),
            User(name="user2", password="hashed", is_active=True, is_reporter=False),
        ]
        mock_users_repo.get_users = AsyncMock(return_value=users)

        service = UsersService(mock_settings, mock_events, mock_users_repo, mock_login_history_repo)
        result = await service.get_users(all=True)
        assert len(result) == 2
        assert result[0].name == "user1"
        assert result[1].name == "user2"


class TestUsersServiceGetLoginHistory:
    @pytest.mark.asyncio
    async def test_get_login_history_returns_list(self):
        mock_settings = MagicMock()
        mock_events = MagicMock()
        mock_users_repo = MagicMock()
        mock_login_history_repo = MagicMock()

        user_id = PydanticObjectId()
        now = datetime.now(timezone.utc)
        histories = [
            LoginHistory(user_id=user_id, login_time=now, ip_address="127.0.0.1"),
            LoginHistory(user_id=user_id, login_time=now, ip_address="192.168.1.1"),
        ]
        mock_login_history_repo.get_login_history = AsyncMock(return_value=histories)

        service = UsersService(mock_settings, mock_events, mock_users_repo, mock_login_history_repo)
        result = await service.get_login_history(user_id)
        assert len(result) == 2
        assert result[0].ip_address == "127.0.0.1"
        assert result[1].ip_address == "192.168.1.1"


class TestUsersServiceSaveUser:
    @pytest.mark.asyncio
    async def test_save_user_creates_new_user(self):
        mock_settings = MagicMock()
        mock_events = MagicMock()
        mock_users_repo = MagicMock()
        mock_login_history_repo = MagicMock()

        mock_users_repo.get_user_by_id = AsyncMock(return_value=None)
        mock_users_repo.create_user = AsyncMock(return_value="new-user-id")

        service = UsersService(mock_settings, mock_events, mock_users_repo, mock_login_history_repo)
        user_id, reset_token = await service.save_user(
            id=None, name="newuser", is_active=True, is_reporter=False, report_mode=ReportMode.EVENT
        )
        assert user_id == "new-user-id"
        assert reset_token is not None
        mock_users_repo.create_user.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_user_updates_existing_user(self):
        mock_settings = MagicMock()
        mock_events = MagicMock()
        mock_users_repo = MagicMock()
        mock_login_history_repo = MagicMock()

        user = User(name="existing", password="hashed", is_active=True, is_reporter=False)
        user.id = PydanticObjectId()
        mock_users_repo.get_user_by_id = AsyncMock(return_value=user)
        mock_users_repo.update_user = AsyncMock(return_value="existing-id")

        service = UsersService(mock_settings, mock_events, mock_users_repo, mock_login_history_repo)
        user_id, reset_token = await service.save_user(
            id=str(user.id), name="updated", is_active=True, is_reporter=False, report_mode=ReportMode.EVENT
        )
        assert user_id == str(user.id)
        assert reset_token is None
        mock_users_repo.update_user.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_user_reporter_no_reset_token(self):
        mock_settings = MagicMock()
        mock_events = MagicMock()
        mock_users_repo = MagicMock()
        mock_login_history_repo = MagicMock()

        mock_users_repo.get_user_by_id = AsyncMock(return_value=None)
        mock_users_repo.create_user = AsyncMock(return_value="new-id")

        service = UsersService(mock_settings, mock_events, mock_users_repo, mock_login_history_repo)
        user_id, reset_token = await service.save_user(
            id=None, name="reporter", is_active=True, is_reporter=True, report_mode=ReportMode.EVENT
        )
        assert user_id == "new-id"
        assert reset_token is None


class TestUsersServiceDeleteUser:
    @pytest.mark.asyncio
    async def test_delete_user_success(self):
        mock_settings = MagicMock()
        mock_events = MagicMock()
        mock_users_repo = MagicMock()
        mock_login_history_repo = MagicMock()

        mock_users_repo.delete_user = AsyncMock(return_value=True)

        service = UsersService(mock_settings, mock_events, mock_users_repo, mock_login_history_repo)
        result = await service.delete_user("user-id")
        assert result is True

    @pytest.mark.asyncio
    async def test_delete_user_failure(self):
        mock_settings = MagicMock()
        mock_events = MagicMock()
        mock_users_repo = MagicMock()
        mock_login_history_repo = MagicMock()

        mock_users_repo.delete_user = AsyncMock(return_value=False)

        service = UsersService(mock_settings, mock_events, mock_users_repo, mock_login_history_repo)
        result = await service.delete_user("user-id")
        assert result is False


class TestUsersServiceCreateReporterToken:
    @pytest.mark.asyncio
    async def test_create_reporter_token_for_reporter(self):
        mock_settings = MagicMock()
        mock_settings.JWT_SECRET_KEY = "test-secret"
        mock_events = MagicMock()
        mock_users_repo = MagicMock()
        mock_login_history_repo = MagicMock()

        user = User(name="reporter", password="hashed", is_reporter=True, report_mode=ReportMode.EVENT)
        mock_users_repo.get_user_by_id = AsyncMock(return_value=user)
        mock_users_repo.save_user_api_key = AsyncMock()

        service = UsersService(mock_settings, mock_events, mock_users_repo, mock_login_history_repo)
        token = await service.create_reporter_token(str(user.id))
        assert token is not None
        mock_users_repo.save_user_api_key.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_reporter_token_for_non_reporter(self):
        mock_settings = MagicMock()
        mock_events = MagicMock()
        mock_users_repo = MagicMock()
        mock_login_history_repo = MagicMock()

        user = User(name="regular", password="hashed", is_reporter=False)
        mock_users_repo.get_user_by_id = AsyncMock(return_value=user)
        mock_users_repo.save_user_api_key = AsyncMock()

        service = UsersService(mock_settings, mock_events, mock_users_repo, mock_login_history_repo)
        token = await service.create_reporter_token(str(user.id))
        assert token is not None
        mock_users_repo.save_user_api_key.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_reporter_token_user_not_found(self):
        mock_settings = MagicMock()
        mock_events = MagicMock()
        mock_users_repo = MagicMock()
        mock_login_history_repo = MagicMock()

        mock_users_repo.get_user_by_id = AsyncMock(return_value=None)

        service = UsersService(mock_settings, mock_events, mock_users_repo, mock_login_history_repo)
        with pytest.raises(ValueError, match="User not found"):
            await service.create_reporter_token("nonexistent")


class TestUsersServiceDeleteReporterToken:
    @pytest.mark.asyncio
    async def test_delete_reporter_token_success(self):
        mock_settings = MagicMock()
        mock_events = MagicMock()
        mock_users_repo = MagicMock()
        mock_login_history_repo = MagicMock()

        user = User(name="reporter", password="hashed", is_reporter=True, report_mode=ReportMode.EVENT)
        mock_users_repo.get_user_by_id = AsyncMock(return_value=user)
        mock_users_repo.save_user_api_key = AsyncMock(return_value=True)

        service = UsersService(mock_settings, mock_events, mock_users_repo, mock_login_history_repo)
        result = await service.delete_reporter_token(str(user.id))
        assert result is True

    @pytest.mark.asyncio
    async def test_delete_reporter_token_user_not_found(self):
        mock_settings = MagicMock()
        mock_events = MagicMock()
        mock_users_repo = MagicMock()
        mock_login_history_repo = MagicMock()

        mock_users_repo.get_user_by_id = AsyncMock(return_value=None)

        service = UsersService(mock_settings, mock_events, mock_users_repo, mock_login_history_repo)
        with pytest.raises(ValueError, match="User not found"):
            await service.delete_reporter_token("nonexistent")

    @pytest.mark.asyncio
    async def test_save_user_exception_handled(self):
        """Test save_user handles exceptions."""
        mock_settings = MagicMock()
        mock_events = MagicMock()
        mock_users_repo = MagicMock()
        mock_login_history_repo = MagicMock()

        mock_users_repo.get_user_by_id = AsyncMock(side_effect=Exception("DB error"))

        service = UsersService(mock_settings, mock_events, mock_users_repo, mock_login_history_repo)
        user_id, reset_token = await service.save_user(
            id="user-id", name="test", is_active=True, is_reporter=False, report_mode=ReportMode.EVENT
        )
        assert user_id is None
        assert reset_token is None

    @pytest.mark.asyncio
    async def test_save_user_non_reporter_generates_reset_token(self):
        """Test save_user generates password reset token for non-reporter."""
        mock_settings = MagicMock()
        mock_events = MagicMock()
        mock_users_repo = MagicMock()
        mock_login_history_repo = MagicMock()

        mock_users_repo.get_user_by_id = AsyncMock(return_value=None)
        mock_users_repo.create_user = AsyncMock(return_value="new-id")

        service = UsersService(mock_settings, mock_events, mock_users_repo, mock_login_history_repo)
        user_id, reset_token = await service.save_user(
            id=None, name="regular", is_active=True, is_reporter=False, report_mode=ReportMode.EVENT
        )
        assert user_id == "new-id"
        assert reset_token is not None

    @pytest.mark.asyncio
    async def test_save_user_reporter_no_reset_token(self):
        """Test save_user does not generate reset token for reporter."""
        mock_settings = MagicMock()
        mock_settings.JWT_SECRET_KEY = "test-secret"
        mock_events = MagicMock()
        mock_users_repo = MagicMock()
        mock_login_history_repo = MagicMock()

        mock_users_repo.get_user_by_id = AsyncMock(return_value=None)
        mock_users_repo.create_user = AsyncMock(return_value="new-id")

        service = UsersService(mock_settings, mock_events, mock_users_repo, mock_login_history_repo)
        user_id, reset_token = await service.save_user(
            id=None, name="reporter", is_active=True, is_reporter=True, report_mode=ReportMode.EVENT
        )
        assert user_id == "new-id"
        assert reset_token is None

    @pytest.mark.asyncio
    async def test_save_user_update_exception_handled(self):
        """Test save_user handles exception when updating existing user."""
        mock_settings = MagicMock()
        mock_events = MagicMock()
        mock_users_repo = MagicMock()
        mock_login_history_repo = MagicMock()

        user = User(name="existing", password="hashed", is_active=True, is_reporter=False)
        user.id = PydanticObjectId()
        mock_users_repo.get_user_by_id = AsyncMock(return_value=user)
        mock_users_repo.update_user = AsyncMock(side_effect=Exception("DB error"))

        service = UsersService(mock_settings, mock_events, mock_users_repo, mock_login_history_repo)
        user_id, reset_token = await service.save_user(
            id=str(user.id), name="updated", is_active=True, is_reporter=False, report_mode=ReportMode.EVENT
        )
        assert user_id is None
        assert reset_token is None

    @pytest.mark.asyncio
    async def test_delete_user_exception_handled(self):
        """Test delete_user handles exceptions."""
        mock_settings = MagicMock()
        mock_events = MagicMock()
        mock_users_repo = MagicMock()
        mock_login_history_repo = MagicMock()

        mock_users_repo.delete_user = AsyncMock(side_effect=Exception("DB error"))

        service = UsersService(mock_settings, mock_events, mock_users_repo, mock_login_history_repo)
        result = await service.delete_user("user-id")
        assert result is False

    @pytest.mark.asyncio
    async def test_create_reporter_token_exception_handled(self):
        """Test create_reporter_token handles exceptions."""
        mock_settings = MagicMock()
        mock_settings.JWT_SECRET_KEY = "test-secret"
        mock_events = MagicMock()
        mock_users_repo = MagicMock()
        mock_login_history_repo = MagicMock()

        user = User(name="reporter", password="hashed", is_reporter=True, report_mode=ReportMode.EVENT)
        mock_users_repo.get_user_by_id = AsyncMock(return_value=user)
        mock_users_repo.save_user_api_key = AsyncMock(side_effect=Exception("DB error"))

        service = UsersService(mock_settings, mock_events, mock_users_repo, mock_login_history_repo)
        with pytest.raises(Exception):
            await service.create_reporter_token(str(user.id))

    @pytest.mark.asyncio
    async def test_delete_reporter_token_exception_handled(self):
        """Test delete_reporter_token handles exceptions."""
        mock_settings = MagicMock()
        mock_events = MagicMock()
        mock_users_repo = MagicMock()
        mock_login_history_repo = MagicMock()

        user = User(name="reporter", password="hashed", is_reporter=True, report_mode=ReportMode.EVENT)
        mock_users_repo.get_user_by_id = AsyncMock(return_value=user)
        mock_users_repo.save_user_api_key = AsyncMock(side_effect=Exception("DB error"))

        service = UsersService(mock_settings, mock_events, mock_users_repo, mock_login_history_repo)
        with pytest.raises(Exception):
            await service.delete_reporter_token(str(user.id))
