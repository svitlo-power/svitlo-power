"""Tests for app/repositories/implementations/bots.py."""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from beanie import PydanticObjectId

from app.repositories.implementations.bots import BotsRepository
from shared.models.bot import Bot


class TestBotsRepository:
    """Tests for BotsRepository."""

    @pytest.mark.asyncio
    async def test_get_bots_all(self):
        """Test get_bots with all=True."""
        mock_bots = [
            MagicMock(spec=Bot, id=PydanticObjectId("507f1f77bcf86cd799439011")),
            MagicMock(spec=Bot, id=PydanticObjectId("507f1f77bcf86cd799439012")),
        ]
        
        with patch.object(Bot, 'find') as mock_find:
            mock_find.return_value.to_list = AsyncMock(return_value=mock_bots)
            
            repo = BotsRepository()
            result = await repo.get_bots(all=True)
            
            assert len(result) == 2
            mock_find.assert_called_once_with({})

    @pytest.mark.asyncio
    async def test_get_bots_enabled_only(self):
        """Test get_bots with all=False (enabled only)."""
        mock_bots = [
            MagicMock(spec=Bot, id=PydanticObjectId("507f1f77bcf86cd799439011")),
        ]
        
        with patch.object(Bot, 'find') as mock_find:
            mock_find.return_value.to_list = AsyncMock(return_value=mock_bots)
            
            repo = BotsRepository()
            result = await repo.get_bots(all=False)
            
            assert len(result) == 1
            mock_find.assert_called_once_with({"enabled": True})

    @pytest.mark.asyncio
    async def test_get_bot_found(self):
        """Test get_bot when bot exists."""
        bot_id = PydanticObjectId("507f1f77bcf86cd799439011")
        mock_bot = MagicMock(spec=Bot, id=bot_id)
        
        with patch.object(Bot, 'get') as mock_get:
            mock_get.return_value = mock_bot
            
            repo = BotsRepository()
            result = await repo.get_bot(bot_id)
            
            assert result == mock_bot
            mock_get.assert_called_once_with(bot_id)

    @pytest.mark.asyncio
    async def test_get_bot_not_found(self):
        """Test get_bot when bot doesn't exist."""
        bot_id = PydanticObjectId("507f1f77bcf86cd799439011")
        
        with patch.object(Bot, 'get') as mock_get:
            mock_get.return_value = None
            
            repo = BotsRepository()
            result = await repo.get_bot(bot_id)
            
            assert result is None

    @pytest.mark.asyncio
    async def test_create_bot(self):
        """Test create_bot."""
        data = {"token": "test_token", "enabled": True}
        mock_bot = MagicMock(spec=Bot, **data)
        
        with patch('app.repositories.implementations.bots.Bot') as mock_bot_class:
            mock_bot_class.return_value = mock_bot
            mock_bot.save = AsyncMock()
            
            repo = BotsRepository()
            result = await repo.create_bot(data)
            
            assert result == mock_bot
            mock_bot.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_bot_success(self):
        """Test update_bot when bot exists."""
        bot_id = PydanticObjectId("507f1f77bcf86cd799439011")
        data = {"enabled": False}
        mock_bot = MagicMock(spec=Bot, id=bot_id)
        
        with patch.object(Bot, 'get') as mock_get:
            mock_get.return_value = mock_bot
            mock_bot.save = AsyncMock()
            
            repo = BotsRepository()
            result = await repo.update_bot(bot_id, data)
            
            assert result == mock_bot
            mock_bot.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_bot_not_found(self):
        """Test update_bot when bot doesn't exist."""
        bot_id = PydanticObjectId("507f1f77bcf86cd799439011")
        data = {"enabled": False}
        
        with patch.object(Bot, 'get') as mock_get:
            mock_get.return_value = None
            
            repo = BotsRepository()
            result = await repo.update_bot(bot_id, data)
            
            assert result is None

    @pytest.mark.asyncio
    async def test_get_is_hook_enabled_true(self):
        """Test get_is_hook_enabled when hook is enabled."""
        bot_id = PydanticObjectId("507f1f77bcf86cd799439011")
        mock_bot = MagicMock(spec=Bot, id=bot_id, hook_enabled=True)
        
        with patch.object(Bot, 'get') as mock_get:
            mock_get.return_value = mock_bot
            
            repo = BotsRepository()
            result = await repo.get_is_hook_enabled(bot_id)
            
            assert result is True

    @pytest.mark.asyncio
    async def test_get_is_hook_enabled_false(self):
        """Test get_is_hook_enabled when hook is disabled."""
        bot_id = PydanticObjectId("507f1f77bcf86cd799439011")
        mock_bot = MagicMock(spec=Bot, id=bot_id, hook_enabled=False)
        
        with patch.object(Bot, 'get') as mock_get:
            mock_get.return_value = mock_bot
            
            repo = BotsRepository()
            result = await repo.get_is_hook_enabled(bot_id)
            
            assert result is False

    @pytest.mark.asyncio
    async def test_get_is_hook_enabled_not_found(self):
        """Test get_is_hook_enabled when bot doesn't exist."""
        bot_id = PydanticObjectId("507f1f77bcf86cd799439011")
        
        with patch.object(Bot, 'get') as mock_get:
            mock_get.return_value = None
            
            repo = BotsRepository()
            result = await repo.get_is_hook_enabled(bot_id)
            
            assert result is False