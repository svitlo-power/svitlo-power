"""Tests for app/repositories/implementations/chats.py."""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime, timezone
from beanie import PydanticObjectId

from app.repositories.implementations.chats import ChatsRepository
from shared.models.chat_request import ChatRequest
from shared.models.allowed_chat import AllowedChat
from shared.models.bot import Bot

# Mock Beanie class-level query attributes to prevent AttributeError when beanie is not initialized
AllowedChat.chat_id = MagicMock()
AllowedChat.bot = MagicMock()
ChatRequest.chat_id = MagicMock()
ChatRequest.bot = MagicMock()


class TestChatsRepository:
    """Tests for ChatsRepository."""

    @pytest.mark.asyncio
    async def test_get_chat_requests(self):
        """Test get_chat_requests."""
        mock_requests = [
            MagicMock(spec=ChatRequest),
            MagicMock(spec=ChatRequest),
        ]
        
        with patch.object(ChatRequest, 'find') as mock_find:
            mock_find.return_value.to_list = AsyncMock(return_value=mock_requests)
            
            repo = ChatsRepository()
            result = await repo.get_chat_requests()
            
            assert len(result) == 2
            mock_find.assert_called_once_with(fetch_links=True)

    @pytest.mark.asyncio
    async def test_get_allowed_chats(self):
        """Test get_allowed_chats."""
        mock_chats = [
            MagicMock(spec=AllowedChat),
            MagicMock(spec=AllowedChat),
        ]
        
        with patch.object(AllowedChat, 'find') as mock_find:
            mock_find.return_value.to_list = AsyncMock(return_value=mock_chats)
            
            repo = ChatsRepository()
            result = await repo.get_allowed_chats()
            
            assert len(result) == 2
            mock_find.assert_called_once_with(fetch_links=True)

    @pytest.mark.asyncio
    async def test_get_is_chat_allowed_true(self):
        """Test get_is_chat_allowed when chat is allowed."""
        chat_id = "123456789"
        bot_id = PydanticObjectId("507f1f77bcf86cd799439011")
        mock_chat = MagicMock(spec=AllowedChat)
        
        with patch.object(AllowedChat, 'find_one', new_callable=AsyncMock) as mock_find_one:
            mock_find_one.return_value = mock_chat
            
            repo = ChatsRepository()
            result = await repo.get_is_chat_allowed(chat_id, bot_id)
            
            assert result is True

    @pytest.mark.asyncio
    async def test_get_is_chat_allowed_false(self):
        """Test get_is_chat_allowed when chat is not allowed."""
        chat_id = "123456789"
        bot_id = PydanticObjectId("507f1f77bcf86cd799439011")
        
        with patch.object(AllowedChat, 'find_one', new_callable=AsyncMock) as mock_find_one:
            mock_find_one.return_value = None
            
            repo = ChatsRepository()
            result = await repo.get_is_chat_allowed(chat_id, bot_id)
            
            assert result is False

    @pytest.mark.asyncio
    async def test_add_chat_request_new(self):
        """Test add_chat_request when request doesn't exist."""
        chat_id = "123456789"
        bot_id = PydanticObjectId("507f1f77bcf86cd799439011")
        mock_bot = MagicMock(spec=Bot, id=bot_id)
        
        with patch.object(ChatRequest, 'find_one', new_callable=AsyncMock) as mock_find_one:
            mock_find_one.return_value = None
            
            with patch.object(Bot, 'get', new_callable=AsyncMock) as mock_bot_get:
                mock_bot_get.return_value = mock_bot
                
                with patch.object(ChatRequest, 'insert', new_callable=AsyncMock) as mock_insert:
                    repo = ChatsRepository()
                    await repo.add_chat_request(chat_id, bot_id)
                    
                    mock_insert.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_chat_request_existing(self):
        """Test add_chat_request when request already exists."""
        chat_id = "123456789"
        bot_id = PydanticObjectId("507f1f77bcf86cd799439011")
        mock_existing = MagicMock(spec=ChatRequest)
        
        with patch.object(ChatRequest, 'find_one', new_callable=AsyncMock) as mock_find_one:
            mock_find_one.return_value = mock_existing
            
            repo = ChatsRepository()
            await repo.add_chat_request(chat_id, bot_id)
            
            # Should not call insert when request exists
            mock_find_one.assert_called_once()

    @pytest.mark.asyncio
    async def test_approve_chat_request_found(self):
        """Test approve_chat_request when request exists."""
        request_id = PydanticObjectId("507f1f77bcf86cd799439011")
        mock_request = MagicMock(spec=ChatRequest)
        mock_request.chat_id = "123456789"
        mock_request.bot = MagicMock(spec=Bot)
        
        with patch.object(ChatRequest, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_request
            
            with patch('app.repositories.implementations.chats.AllowedChat') as mock_allowed_class:
                mock_allowed = MagicMock(spec=AllowedChat)
                mock_allowed_class.return_value = mock_allowed
                mock_allowed.insert = AsyncMock()
                mock_request.delete = AsyncMock()
                
                repo = ChatsRepository()
                await repo.approve_chat_request(request_id)
                
                mock_allowed.insert.assert_called_once()
                mock_request.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_approve_chat_request_not_found(self):
        """Test approve_chat_request when request doesn't exist."""
        request_id = PydanticObjectId("507f1f77bcf86cd799439011")
        
        with patch.object(ChatRequest, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = None
            
            repo = ChatsRepository()
            result = await repo.approve_chat_request(request_id)
            
            assert result is None

    @pytest.mark.asyncio
    async def test_reject_chat_request_found(self):
        """Test reject_chat_request when request exists."""
        request_id = PydanticObjectId("507f1f77bcf86cd799439011")
        mock_request = MagicMock(spec=ChatRequest)
        
        with patch.object(ChatRequest, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_request
            mock_request.delete = AsyncMock()
            
            repo = ChatsRepository()
            await repo.reject_chat_request(request_id)
            
            mock_request.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_reject_chat_request_not_found(self):
        """Test reject_chat_request when request doesn't exist."""
        request_id = PydanticObjectId("507f1f77bcf86cd799439011")
        
        with patch.object(ChatRequest, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = None
            
            repo = ChatsRepository()
            result = await repo.reject_chat_request(request_id)
            
            assert result is None

    @pytest.mark.asyncio
    async def test_disallow_chat_found(self):
        """Test disallow_chat when chat exists."""
        chat_id = PydanticObjectId("507f1f77bcf86cd799439011")
        mock_chat = MagicMock(spec=AllowedChat)
        mock_chat.chat_id = "123456789"
        mock_chat.bot = MagicMock(spec=Bot)
        
        with patch.object(AllowedChat, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_chat
            
            with patch('app.repositories.implementations.chats.ChatRequest') as mock_request_class:
                mock_request = MagicMock(spec=ChatRequest)
                mock_request_class.return_value = mock_request
                mock_request.insert = AsyncMock()
                mock_chat.delete = AsyncMock()
                
                repo = ChatsRepository()
                await repo.disallow_chat(chat_id)
                
                mock_chat.delete.assert_called_once()
                mock_request.insert.assert_called_once()

    @pytest.mark.asyncio
    async def test_disallow_chat_not_found(self):
        """Test disallow_chat when chat doesn't exist."""
        chat_id = PydanticObjectId("507f1f77bcf86cd799439011")
        
        with patch.object(AllowedChat, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = None
            
            repo = ChatsRepository()
            result = await repo.disallow_chat(chat_id)
            
            assert result is None