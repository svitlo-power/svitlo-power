"""Tests for app/repositories/implementations/login_history.py."""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from beanie import PydanticObjectId

from app.repositories.implementations.login_history import LoginHistoryRepository
from shared.models.login_history import LoginHistory

# Mock Beanie class-level query attributes to prevent AttributeError when beanie is not initialized
LoginHistory.login_time = MagicMock()


class TestLoginHistoryRepository:
    """Tests for LoginHistoryRepository."""

    @pytest.mark.asyncio
    async def test_get_login_history(self):
        """Test get_login_history."""
        user_id = PydanticObjectId("507f1f77bcf86cd799439011")
        mock_history = [MagicMock(spec=LoginHistory)]
        
        with patch.object(LoginHistory, 'find') as mock_find:
            mock_find.return_value.sort.return_value.to_list = AsyncMock(return_value=mock_history)
            
            repo = LoginHistoryRepository()
            result = await repo.get_login_history(user_id)
            
            assert result == mock_history
            mock_find.assert_called_once_with({"user_id": user_id}, fetch_links=True)

    @pytest.mark.asyncio
    async def test_add_login_history(self):
        """Test add_login_history."""
        user_id = PydanticObjectId("507f1f77bcf86cd799439011")
        ip = "192.168.1.1"
        mock_id = PydanticObjectId("507f1f77bcf86cd799439012")
        
        with patch('app.repositories.implementations.login_history.LoginHistory') as mock_history_class:
            mock_instance = MagicMock()
            mock_instance.id = mock_id
            mock_instance.insert = AsyncMock()
            mock_history_class.return_value = mock_instance
            
            repo = LoginHistoryRepository()
            result = await repo.add_login_history(user_id, ip)
            
            assert result == mock_id
            mock_instance.insert.assert_called_once()
