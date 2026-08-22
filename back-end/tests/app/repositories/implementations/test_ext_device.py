"""Tests for app/repositories/implementations/ext_device.py."""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from beanie import PydanticObjectId

from app.repositories.implementations.ext_device import ExtDeviceRepository
from shared.models.ext_device import ExtDevice

# Mock Beanie class-level query attributes to prevent AttributeError when beanie is not initialized
ExtDevice.mac_address = MagicMock()


class TestExtDeviceRepository:
    """Tests for ExtDeviceRepository."""

    @pytest.mark.asyncio
    async def test_get_ext_device(self):
        """Test get_ext_device."""
        mac = "00:11:22:33:44:55"
        mock_device = MagicMock(spec=ExtDevice)
        
        with patch.object(ExtDevice, 'find_one', new_callable=AsyncMock) as mock_find_one:
            mock_find_one.return_value = mock_device
            
            repo = ExtDeviceRepository()
            result = await repo.get_ext_device(mac)
            
            assert result == mock_device
            mock_find_one.assert_called_once()

    @pytest.mark.asyncio
    async def test_add_device(self):
        """Test add_device."""
        mock_device = MagicMock(spec=ExtDevice)
        mock_device.id = PydanticObjectId("507f1f77bcf86cd799439011")
        mock_device.insert = AsyncMock()
        
        repo = ExtDeviceRepository()
        result = await repo.add_device(mock_device)
        
        assert result == mock_device.id
        mock_device.insert.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_device(self):
        """Test update_device."""
        mock_device = MagicMock(spec=ExtDevice)
        mock_device.id = PydanticObjectId("507f1f77bcf86cd799439011")
        mock_device.save = AsyncMock()
        
        repo = ExtDeviceRepository()
        result = await repo.update_device(mock_device)
        
        assert result == mock_device.id
        mock_device.save.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_all_devices(self):
        """Test get_all_devices."""
        mock_devices = [MagicMock(spec=ExtDevice)]
        
        with patch.object(ExtDevice, 'find_all') as mock_find_all:
            mock_find_all.return_value.to_list = AsyncMock(return_value=mock_devices)
            
            repo = ExtDeviceRepository()
            result = await repo.get_all_devices()
            
            assert result == mock_devices
            mock_find_all.assert_called_once_with(fetch_links=True)
