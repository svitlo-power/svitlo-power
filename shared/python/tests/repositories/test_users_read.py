"""Tests for shared/repositories/implementations/users_read.py."""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from beanie import PydanticObjectId

from shared.repositories.implementations.users_read import UsersReadRepository
from shared.models.user import User


# Mock Beanie class-level query attributes
User.is_active = MagicMock()
User.name = MagicMock()
User.id = MagicMock()
User.password_reset_token = MagicMock()


class TestUsersReadRepository:
    """Tests for UsersReadRepository."""

    @pytest.mark.asyncio
    async def test_get_user(self):
        """Test get_user by name."""
        mock_user = MagicMock(spec=User)
        with patch.object(User, 'find_one', new_callable=AsyncMock) as mock_find_one:
            mock_find_one.return_value = mock_user
            repo = UsersReadRepository()
            result = await repo.get_user("alice")
            assert result == mock_user

    @pytest.mark.asyncio
    async def test_get_users_all(self):
        """Test get_users with all=True."""
        mock_users = [MagicMock(spec=User)]
        with patch.object(User, 'find') as mock_find:
            mock_find.return_value.to_list = AsyncMock(return_value=mock_users)
            repo = UsersReadRepository()
            result = await repo.get_users(all=True)
            assert result == mock_users
            mock_find.assert_called_once_with({})

    @pytest.mark.asyncio
    async def test_get_users_active_only(self):
        """Test get_users with all=False."""
        mock_users = [MagicMock(spec=User)]
        with patch.object(User, 'find') as mock_find:
            mock_find.return_value.to_list = AsyncMock(return_value=mock_users)
            repo = UsersReadRepository()
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
            repo = UsersReadRepository()
            result = await repo.get_user_by_id(user_id)
            assert result == mock_user

    @pytest.mark.asyncio
    async def test_get_user_by_reset_token(self):
        """Test get_user_by_reset_token."""
        mock_user = MagicMock(spec=User)
        with patch.object(User, 'find_one', new_callable=AsyncMock) as mock_find_one:
            mock_find_one.return_value = mock_user
            repo = UsersReadRepository()
            result = await repo.get_user_by_reset_token("some-token")
            assert result == mock_user