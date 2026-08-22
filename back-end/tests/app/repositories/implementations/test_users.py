"""Tests for app/repositories/implementations/users.py."""
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
    """Tests for UsersRepository."""

    @pytest.mark.asyncio
    async def test_get_user(self):
        """Test get_user by name."""
        mock_user = MagicMock(spec=User)
        with patch.object(User, 'find_one', new_callable=AsyncMock) as mock_find_one:
            mock_find_one.return_value = mock_user
            repo = UsersRepository()
            result = await repo.get_user("alice")
            assert result == mock_user

    @pytest.mark.asyncio
    async def test_get_users_all(self):
        """Test get_users with all=True."""
        mock_users = [MagicMock(spec=User)]
        with patch.object(User, 'find') as mock_find:
            mock_find.return_value.to_list = AsyncMock(return_value=mock_users)
            repo = UsersRepository()
            result = await repo.get_users(all=True)
            assert result == mock_users
            mock_find.assert_called_once_with({})

    @pytest.mark.asyncio
    async def test_get_users_active_only(self):
        """Test get_users with all=False."""
        mock_users = [MagicMock(spec=User)]
        with patch.object(User, 'find') as mock_find:
            mock_find.return_value.to_list = AsyncMock(return_value=mock_users)
            repo = UsersRepository()
            result = await repo.get_users(all=False)
            assert result == mock_users
            mock_find.assert_called_once_with({"is_active": True})

    @pytest.mark.asyncio
    async def test_get_user_by_id(self):
        """Test get_user_by_id."""
        user_id = str(PydanticObjectId("507f1f77bcf86cd799439011"))
        mock_user = MagicMock(spec=User)
        with patch.object(User, 'find_one', new_callable=AsyncMock) as mock_find_one:
            mock_find_one.return_value = mock_user
            repo = UsersRepository()
            result = await repo.get_user_by_id(user_id)
            assert result == mock_user

    @pytest.mark.asyncio
    async def test_get_user_by_reset_token(self):
        """Test get_user_by_reset_token."""
        mock_user = MagicMock(spec=User)
        with patch.object(User, 'find_one', new_callable=AsyncMock) as mock_find_one:
            mock_find_one.return_value = mock_user
            repo = UsersRepository()
            result = await repo.get_user_by_reset_token("some-token")
            assert result == mock_user

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
        expiry = datetime.now()
        with patch.object(repo, 'get_user_by_id', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_user
            await repo.set_password_reset_token(user_id, "token123", expiry)
            assert mock_user.password_reset_token == "token123"
            assert mock_user.reset_token_expiration == expiry
            mock_user.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_set_password_reset_token_not_found(self):
        """Test set_password_reset_token raises ValueError when not found."""
        user_id = str(PydanticObjectId("507f1f77bcf86cd799439011"))
        repo = UsersRepository()
        with patch.object(repo, 'get_user_by_id', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = None
            with pytest.raises(ValueError):
                await repo.set_password_reset_token(user_id, "token", datetime.now())

    def test_remove_password_reset_token_private(self):
        """Test _remove_password_reset_token."""
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
        mock_user.save = MagicMock()  # NOTE: not awaited in production code
        repo = UsersRepository()
        with patch.object(repo, 'get_user_by_id', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_user
            await repo.remove_password_reset_token(user_id)
            assert mock_user.password_reset_token is None
            assert mock_user.reset_token_expiration is None

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
            mock_user.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_change_password_not_found(self):
        """Test change_password when not found does nothing."""
        user_id = str(PydanticObjectId("507f1f77bcf86cd799439011"))
        repo = UsersRepository()
        with patch.object(repo, 'get_user_by_id', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = None
            await repo.change_password(user_id, "new_password")  # Should not raise

    @pytest.mark.asyncio
    async def test_create_user_new(self):
        """Test create_user when user doesn't exist."""
        expiry = datetime.now()
        repo = UsersRepository()
        with patch.object(repo, 'get_user', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = None
            with patch.object(User, 'insert', new_callable=AsyncMock) as mock_insert:
                result = await repo.create_user("alice", True, False, "token", expiry, ReportMode.PING)
                mock_insert.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_user_existing(self):
        """Test create_user when user already exists returns None."""
        expiry = datetime.now()
        repo = UsersRepository()
        with patch.object(repo, 'get_user', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MagicMock(spec=User)
            result = await repo.create_user("alice", True, False, "token", expiry, ReportMode.PING)
            assert result is None

    @pytest.mark.asyncio
    async def test_force_create_user_new(self):
        """Test force_create_user when user doesn't exist."""
        repo = UsersRepository()
        with patch.object(repo, 'get_user', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = None
            with patch.object(User, 'insert', new_callable=AsyncMock) as mock_insert:
                result = await repo.force_create_user("alice", "password")
                mock_insert.assert_called_once()

    @pytest.mark.asyncio
    async def test_force_create_user_existing(self):
        """Test force_create_user when user already exists returns None."""
        repo = UsersRepository()
        with patch.object(repo, 'get_user', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = MagicMock(spec=User)
            result = await repo.force_create_user("alice", "password")
            assert result is None

    @pytest.mark.asyncio
    async def test_update_user_not_found(self):
        """Test update_user when user not found returns early."""
        user_id = str(PydanticObjectId("507f1f77bcf86cd799439011"))
        repo = UsersRepository()
        with patch.object(repo, 'get_user_by_id', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = None
            await repo.update_user(user_id, "alice", True, False, ReportMode.PING)  # No error

    @pytest.mark.asyncio
    async def test_update_user_reporter_to_non_reporter(self):
        """Test update_user: reporter -> non-reporter clears api_key and tokens."""
        user_id = str(PydanticObjectId("507f1f77bcf86cd799439011"))
        mock_user = MagicMock(spec=User)
        mock_user.is_reporter = True
        mock_user.api_key = "some-key"
        mock_user.save = AsyncMock()
        repo = UsersRepository()
        with patch.object(repo, 'get_user_by_id', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_user
            await repo.update_user(user_id, "alice", True, False, ReportMode.PING)
            assert mock_user.api_key is None
            assert mock_user.password_reset_token is None
            mock_user.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_user_normal(self):
        """Test update_user normal update."""
        user_id = str(PydanticObjectId("507f1f77bcf86cd799439011"))
        mock_user = MagicMock(spec=User)
        mock_user.is_reporter = False
        mock_user.api_key = None
        mock_user.save = AsyncMock()
        repo = UsersRepository()
        with patch.object(repo, 'get_user_by_id', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_user
            await repo.update_user(user_id, "alice", True, True, ReportMode.PING)
            assert mock_user.name == "alice"
            assert mock_user.is_active is True
            assert mock_user.is_reporter is True
            mock_user.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_user_found(self):
        """Test delete_user when user exists."""
        user_id = str(PydanticObjectId("507f1f77bcf86cd799439011"))
        mock_user = MagicMock(spec=User)
        mock_user.delete = AsyncMock()
        repo = UsersRepository()
        with patch.object(repo, 'get_user_by_id', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_user
            result = await repo.delete_user(user_id)
            assert result is True
            mock_user.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_user_not_found(self):
        """Test delete_user when user not found."""
        user_id = str(PydanticObjectId("507f1f77bcf86cd799439011"))
        repo = UsersRepository()
        with patch.object(repo, 'get_user_by_id', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = None
            result = await repo.delete_user(user_id)
            assert result is False

    @pytest.mark.asyncio
    async def test_save_user_api_key_found(self):
        """Test save_user_api_key when user exists."""
        user_id = str(PydanticObjectId("507f1f77bcf86cd799439011"))
        mock_user = MagicMock(spec=User)
        mock_user.save = AsyncMock()
        repo = UsersRepository()
        with patch.object(repo, 'get_user_by_id', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_user
            result = await repo.save_user_api_key(user_id, "api-key-123")
            assert result is True
            assert mock_user.api_key == "api-key-123"
            mock_user.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_user_api_key_not_found(self):
        """Test save_user_api_key when user not found."""
        user_id = str(PydanticObjectId("507f1f77bcf86cd799439011"))
        repo = UsersRepository()
        with patch.object(repo, 'get_user_by_id', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = None
            result = await repo.save_user_api_key(user_id, "api-key-123")
            assert result is False
