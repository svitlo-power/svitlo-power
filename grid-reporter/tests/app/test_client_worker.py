"""Tests for grid-reporter client worker."""
import asyncio
import pytest
from unittest.mock import MagicMock, patch, AsyncMock

from app.client_worker import ClientWorker
from app.config import ClientConfig
from app.settings import Settings
from app.state_store import StateStore
from shared.services.deye_api import BaseDeyeClient


class TestClientWorker:
    def test_init(self):
        """Test ClientWorker initialization."""
        mock_client = MagicMock(spec=ClientConfig)
        mock_client.client_id = "test_client"
        mock_client.poll_interval = 240
        mock_client.station_id = "station_1"
        
        mock_deye_client = MagicMock()
        mock_session = MagicMock()
        mock_state_store = MagicMock()
        mock_settings = MagicMock()
        mock_settings.poll_interval = 240
        
        worker = ClientWorker(mock_client, mock_deye_client, mock_session, mock_state_store, mock_settings)
        
        assert worker.client == mock_client
        assert worker.settings.poll_interval == 240

    @pytest.mark.asyncio
    async def testpoll_and_sync_no_change(self):
        """Test poll_and_sync when grid state unchanged."""
        mock_client = MagicMock(spec=ClientConfig)
        mock_client.client_id = "test_client"
        mock_client.poll_interval = 240
        mock_client.station_id = "station_1"
        
        mock_deye_client = MagicMock()
        mock_deye_client.get_station_data = AsyncMock(return_value={
            "success": True,
            "data": {"grid_state": True}
        })
        
        mock_session = MagicMock()
        mock_state_store = MagicMock()
        mock_state_store.load.return_value = {"grid_state": True}
        
        mock_settings = MagicMock()
        mock_settings.poll_interval = 240
        
        worker = ClientWorker(mock_client, mock_deye_client, mock_session, mock_state_store, mock_settings)
        
        # Mock send_ext_data to return False (not sent)
        with patch("app.client_worker.send_ext_data", new_callable=AsyncMock) as mock_send:
            mock_send.return_value = False
            
            await worker.poll_and_sync()
            
            # Should not send if state unchanged
            mock_send.assert_not_called()
            mock_state_store.save.assert_not_called()

    @pytest.mark.asyncio
    async def testpoll_and_sync_state_changed(self):
        """Test poll_and_sync when grid state changes."""
        mock_client = MagicMock(spec=ClientConfig)
        mock_client.client_id = "test_client"
        mock_client.poll_interval = 240
        mock_client.station_id = "station_1"
        
        mock_deye_client = MagicMock()
        mock_deye_client.get_station_data = AsyncMock(return_value={
            "success": True,
            "data": {"grid_state": False}
        })
        
        mock_session = MagicMock()
        mock_state_store = MagicMock()
        mock_state_store.load.return_value = {"grid_state": True}
        
        mock_settings = MagicMock()
        mock_settings.poll_interval = 240
        
        worker = ClientWorker(mock_client, mock_deye_client, mock_session, mock_state_store, mock_settings)
        
        with patch("app.client_worker.send_ext_data", new_callable=AsyncMock) as mock_send:
            mock_send.return_value = True
            
            await worker.poll_and_sync()
            
            # Should send and save when state changes
            mock_send.assert_called_once()
            mock_state_store.save.assert_called_once()

    @pytest.mark.asyncio
    async def testpoll_and_sync_deye_unavailable(self):
        """Test poll_and_sync when Deye data unavailable."""
        mock_client = MagicMock(spec=ClientConfig)
        mock_client.client_id = "test_client"
        mock_client.poll_interval = 240
        mock_client.station_id = "station_1"
        
        mock_deye_client = MagicMock()
        mock_deye_client.get_station_data = AsyncMock(return_value={
            "success": False
        })
        
        mock_session = MagicMock()
        mock_state_store = MagicMock()
        mock_settings = MagicMock()
        mock_settings.poll_interval = 240
        
        worker = ClientWorker(mock_client, mock_deye_client, mock_session, mock_state_store, mock_settings)
        
        await worker.poll_and_sync()
        
        # Should not save or send when Deye unavailable
        mock_state_store.save.assert_not_called()
