"""Tests for app/repositories/implementations/users.py - write methods only.
Read methods are tested in shared/python/tests/repositories/test_users_read.py
"""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime
from beanie import PydanticObjectId

from app.repositories.implementations.users import UsersRepository
from shared.models.user import User, ReportMode

# Mock Beanie class-level query attributes
User.is_active = MagicMock()
User.name = MagicMock()
User.id = MagicMock()
User.password_reset_token = MagicMock()


class TestUsersRepository:
    """Tests for UsersRepository write methods."""

    @pytest.mark.asyncio
    async def test_rename_user_found(self):
        """Test rename_user when user found."""
        user_id = str(PydanticObjectId("507f1f77bcf86cd799439011"))
        mock_user = MagicMock(spec=User)
        mock_user.save = AsyncMock()
        repo = UsersRepository()
        with patch.object(repo, 'get_user_by_id', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_user
            await repo.rename_user(user_id, "new_name")
            assert mock_user.name == "new_name"
            mock_user.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_rename_user_not_found(self):
        """Test rename_user when user not found does nothing."""
        user_id = str(PydanticObjectId("507f1f77bcf86cd799439011"))
        repo = UsersRepository()
        with patch.object(repo, 'get_user_by_id', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = None
            await repo.rename_user(user_id, "new_name")  # Should not raise

    @pytest.mark.asyncio
    async def test_set_password_reset_token_found(self):
        """Test set_password_reset_token when user found."""
        user_id = str(PydanticObjectId("507f1f77bcf86cd799439011"))
        mock_user = MagicMock(spec=User)
        mock_user.save = AsyncMock()
        repo = UsersRepository()
        with patch.object(repo, 'get_user_by_id', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_user
            await repo.set_password_reset_token(user_id, "token", datetime.now())
            assert mock_user.password_reset_token == "token"
            mock_user.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_set_password_reset_token_not_found(self):
        """Test set_password_reset_token when user not found raises ValueError."""
        user_id = str(PydanticObjectId("507f1f77bcf86cd799439011"))
        repo = UsersRepository()
        with patch.object(repo, 'get_user_by_id', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = None
            with pytest.raises(ValueError):
                await repo.set_password_reset_token(user_id, "token", datetime.now())

    @pytest.mark.asyncio
    async def test_remove_password_reset_token_private(self):
        """Test _remove_password_reset_token private method."""
        mock_user = MagicMock(spec=User)
        repo = UsersRepository()
        repo._remove_password_reset_token(mock_user)
        assert mock_user.password_reset_token is None
        assert mock_user.reset_token_expiration is None

    @pytest.mark.asyncio
    async def test_remove_password_reset_token_found(self):
        """Test remove_password_reset_token when user found."""
        user_id = str(PydanticObjectId("507f1f77bcf86cd799439011"))
        mock_user = MagicMock(spec=User)
        mock_user.save = AsyncMock()
        repo = UsersRepository()
        with patch.object(repo, 'get_user_by_id', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_user
            await repo.remove_password_reset_token(user_id)
            assert mock_user.password_reset_token is None
            assert mock_user.reset_token_expiration is None
            mock_user.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_change_password_found(self):
        """Test change_password when user found."""
        user_id = str(PydanticObjectId("507f1f77bcf86cd799439011"))
        mock_user = MagicMock(spec=User)
        mock_user.save = AsyncMock()
        repo = UsersRepository()
        with patch.object(repo, 'get_user_by_id', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_user
            await repo.change_password(user_id, "new_password")
            assert mock_user.password == "new_password"
            assert mock_user.password_reset_token is None
            assert mock_user.reset_token_expiration is None
            mock_user.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_change_password_not_found(self):
        """Test change_password when user not found does nothing."""
        user_id = str(PydanticObjectId("507f1f77bcf86cd799439011"))
        repo = UsersRepository()
        with patch.object(repo, 'get_user_by_id', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = None
            await repo.change_password(user_id, "new_password")  # Should not raise

    @pytest.mark.asyncio
    async def test_create_user_new(self):
        """Test create_user creates new user."""
        repo = UsersRepository()
        with patch.object(repo, 'get_user', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = None
            with patch('app.repositories.implementations.users.User') as MockUser:
                mock_user_instance = MagicMock()
                mock_user_instance.id = PydanticObjectId("507f1f77bcf86cd799439011")
                mock_user_instance.insert = AsyncMock()
                MockUser.return_value = mock_user_instance
                result = await repo.create_user("alice", True, False, "token", "2024-01-01", ReportMode.PING)
                assert result == PydanticObjectId("507f1f77bcf86cd799439011")
                mock_user_instance.insert.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_user_existing(self):
        """Test create_user returns None when user exists."""
        mock_user = MagicMock(spec=User)
        repo = UsersRepository()
        with patch.object(repo, 'get_user', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_user
            result = await repo.create_user("alice", True, False, "token", "2024-01-01", ReportMode.PING)
            assert result is None

    @pytest.mark.asyncio
    async def test_force_create_user_new(self):
        """Test force_create_user creates new user."""
        repo = UsersRepository()
        with patch.object(repo, 'get_user', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = None
            with patch('app.repositories.implementations.users.User') as MockUser:
                mock_user_instance = MagicMock()
                mock_user_instance.id = PydanticObjectId("507f1f77bcf86cd799439011")
                mock_user_instance.insert = AsyncMock()
                MockUser.return_value = mock_user_instance
                result = await repo.force_create_user("alice", "password")
                assert result == PydanticObjectId("507f1f77bcf86cd799439011")
                mock_user_instance.insert.assert_called_once()

    @pytest.mark.asyncio
    async def test_force_create_user_existing(self):
        """Test force_create_user returns None when user exists."""
        mock_user = MagicMock(spec=User)
        repo = UsersRepository()
        with patch.object(repo, 'get_user', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_user
            result = await repo.force_create_user("alice", "password")
            assert result is None

    @pytest.mark.asyncio
    async def test_update_user_not_found(self):
        """Test update_user when user not found returns None."""
        repo = UsersRepository()
        with patch.object(repo, 'get_user_by_id', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = None
            result = await repo.update_user("id", "name", True, True, ReportMode.PING)
            assert result is None

    @pytest.mark.asyncio
    async def test_update_user_reporter_to_non_reporter(self):
        """Test update_user from reporter to non-reporter."""
        mock_user = MagicMock(spec=User)
        mock_user.save = AsyncMock()
        mock_user.is_reporter = True
        mock_user.api_key = "some_key"
        repo = UsersRepository()
        with patch.object(repo, 'get_user_by_id', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_user
            result = await repo.update_user("id", "name", True, False, ReportMode.PING)
            assert mock_user.is_reporter is False
            assert mock_user.api_key is None
            mock_user.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_user_normal(self):
        """Test update_user normal update."""
        mock_user = MagicMock(spec=User)
        mock_user.save = AsyncMock()
        mock_user.is_reporter = False
        repo = UsersRepository()
        with patch.object(repo, 'get_user_by_id', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_user
            result = await repo.update_user("id", "new_name", True, True, ReportMode.EVENT)
            assert mock_user.name == "new_name"
            assert mock_user.is_active is True
            assert mock_user.is_reporter is True
            assert mock_user.report_mode == ReportMode.EVENT
            mock_user.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_user_found(self):
        """Test delete_user when user found."""
        user_id = str(PydanticObjectId("507f1f77bcf86cd799439011"))
        mock_user = MagicMock(spec=User)
        mock_user.delete = AsyncMock()
        repo = UsersRepository()
        with patch.object(repo, 'get_user_by_id', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_user
            await repo.delete_user(user_id)
            mock_user.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_user_not_found(self):
        """Test delete_user when user not found does nothing."""
        user_id = str(PydanticObjectId("507f1f77bcf86cd799439011"))
        repo = UsersRepository()
        with patch.object(repo, 'get_user_by_id', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = None
            await repo.delete_user(user_id)  # Should not raise

    @pytest.mark.asyncio
    async def test_save_user_api_key_found(self):
        """Test save_user_api_key when user found."""
        user_id = str(PydanticObjectId("507f1f77bcf86cd799439011"))
        mock_user = MagicMock(spec=User)
        mock_user.save = AsyncMock()
        repo = UsersRepository()
        with patch.object(repo, 'get_user_by_id', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_user
            result = await repo.save_user_api_key(user_id, "api_key")
            assert result is True
            assert mock_user.api_key == "api_key"
            mock_user.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_user_api_key_not_found(self):
        """Test save_user_api_key when user not found returns False."""
        user_id = str(PydanticObjectId("507f1f77bcf86cd799439011"))
        repo = UsersRepository()
        with patch.object(repo, 'get_user_by_id', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = None
            result = await repo.save_user_api_key(user_id, "api_key")
            assert result is False