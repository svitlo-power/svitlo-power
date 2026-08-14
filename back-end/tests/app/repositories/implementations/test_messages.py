"""Tests for app/repositories/implementations/messages.py."""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime, timezone
from beanie import PydanticObjectId

from app.repositories.implementations.messages import MessagesRepository
from shared.models.message import Message
from shared.models.bot import Bot
from shared.models.station import Station

# Mock Beanie class-level query attributes to prevent AttributeError when beanie is not initialized
Message.id = MagicMock()


class TestMessagesRepository:
    """Tests for MessagesRepository."""

    @pytest.mark.asyncio
    async def test_get_messages_all(self):
        """Test get_messages with all=True."""
        mock_messages = [MagicMock(spec=Message)]
        with patch.object(Message, 'find') as mock_find:
            mock_find.return_value.to_list = AsyncMock(return_value=mock_messages)
            repo = MessagesRepository()
            result = await repo.get_messages(all=True)
            assert result == mock_messages
            mock_find.assert_called_once_with({}, fetch_links=True)

    @pytest.mark.asyncio
    async def test_get_messages_enabled_only(self):
        """Test get_messages with all=False (enabled only)."""
        mock_messages = [MagicMock(spec=Message)]
        with patch.object(Message, 'find') as mock_find:
            mock_find.return_value.to_list = AsyncMock(return_value=mock_messages)
            repo = MessagesRepository()
            result = await repo.get_messages(all=False)
            assert result == mock_messages
            mock_find.assert_called_once_with({"enabled": True}, fetch_links=True)

    @pytest.mark.asyncio
    async def test_get_message(self):
        """Test get_message."""
        msg_id = PydanticObjectId("507f1f77bcf86cd799439011")
        mock_msg = MagicMock(spec=Message)
        with patch.object(Message, 'find_one', new_callable=AsyncMock) as mock_find_one:
            mock_find_one.return_value = mock_msg
            repo = MessagesRepository()
            result = await repo.get_message(msg_id)
            assert result == mock_msg
            mock_find_one.assert_called_once()

    @pytest.mark.asyncio
    async def test_save_state(self):
        """Test save_state."""
        msg_id = PydanticObjectId("507f1f77bcf86cd799439011")
        mock_msg = MagicMock(spec=Message)
        mock_msg.save = AsyncMock()
        
        with patch.object(Message, 'find_one', new_callable=AsyncMock) as mock_find_one:
            mock_find_one.return_value = mock_msg
            repo = MessagesRepository()
            await repo.save_state(msg_id, False)
            assert mock_msg.enabled is False
            mock_msg.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_create(self):
        """Test create message."""
        bot_id = PydanticObjectId("507f1f77bcf86cd799439012")
        station_id = PydanticObjectId("507f1f77bcf86cd799439013")
        mock_bot = MagicMock(spec=Bot)
        mock_station = MagicMock(spec=Station)
        mock_msg = MagicMock(spec=Message)
        mock_msg.insert = AsyncMock(return_value=mock_msg)
        
        # We need mock_msg to have these attributes so hasattr is True
        mock_msg.bot = None
        mock_msg.stations = None
        mock_msg.text_format = "test"
        mock_msg.enabled = True
        
        data = {
            "bot_id": bot_id,
            "stations": [station_id],
            "text_format": "test",
            "enabled": True,
            "invalid_key": "some_value" # to cover logger.warning
        }
        
        with patch('app.repositories.implementations.messages.Message', return_value=mock_msg):
            with patch.object(Bot, 'get', new_callable=AsyncMock) as mock_bot_get:
                mock_bot_get.return_value = mock_bot
                with patch.object(Station, 'get', new_callable=AsyncMock) as mock_station_get:
                    mock_station_get.return_value = mock_station
                    
                    repo = MessagesRepository()
                    result = await repo.create(data)
                    
                    assert result == mock_msg
                    mock_msg.insert.assert_called_once()
                    assert mock_msg.bot == mock_bot
                    assert mock_msg.stations == [mock_station]

    @pytest.mark.asyncio
    async def test_update_not_found(self):
        """Test update when message doesn't exist."""
        msg_id = PydanticObjectId("507f1f77bcf86cd799439011")
        with patch.object(Message, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = None
            repo = MessagesRepository()
            result = await repo.update(msg_id, {})
            assert result is None

    @pytest.mark.asyncio
    async def test_update_success(self):
        """Test update success."""
        msg_id = PydanticObjectId("507f1f77bcf86cd799439011")
        mock_msg = MagicMock(spec=Message)
        mock_msg.save = AsyncMock()
        mock_msg.text_format = "test"
        
        data = {"text_format": "new test"}
        with patch.object(Message, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_msg
            repo = MessagesRepository()
            result = await repo.update(msg_id, data)
            assert result == mock_msg
            assert mock_msg.text_format == "new test"
            mock_msg.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_set_last_sent(self):
        """Test set_last_sent."""
        msg_id = PydanticObjectId("507f1f77bcf86cd799439011")
        mock_msg = MagicMock(spec=Message)
        mock_msg.save = AsyncMock()
        with patch.object(Message, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_msg
            repo = MessagesRepository()
            await repo.set_last_sent(msg_id)
            assert mock_msg.last_sent_time is not None
            mock_msg.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_set_last_sent_not_found(self):
        """Test set_last_sent when message not found."""
        msg_id = PydanticObjectId("507f1f77bcf86cd799439011")
        with patch.object(Message, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = None
            repo = MessagesRepository()
            await repo.set_last_sent(msg_id) # should just return

    @pytest.mark.asyncio
    async def test_update_invalid_key_logs_warning(self):
        """Test update with invalid key logs warning."""
        msg_id = PydanticObjectId("507f1f77bcf86cd799439011")
        mock_msg = MagicMock(spec=Message)
        mock_msg.save = AsyncMock()
        
        with patch.object(Message, 'get', new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_msg
            
            repo = MessagesRepository()
            with patch('app.repositories.implementations.messages.logger') as mock_logger:
                await repo.update(msg_id, {"invalid_key": "value"})
                mock_logger.warning.assert_called_once_with("No attr invalid_key in Message")
