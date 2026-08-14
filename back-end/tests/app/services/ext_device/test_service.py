"""Tests for app/services/ext_device/service.py."""
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest
from beanie import PydanticObjectId

from app.services.ext_device.service import ExtDeviceService
from app.models.api import DevicePingRequest, ExtDeviceResponse
from shared.models.ext_device import ExtDevice
from shared.models.user import User
from shared.models.ext_data import ExtData


class TestExtDeviceServiceInit:
    def test_init_stores_dependencies(self):
        mock_events = MagicMock()
        mock_ext_device_repo = MagicMock()
        mock_users_repo = MagicMock()
        mock_ext_data_repo = MagicMock()

        service = ExtDeviceService(mock_events, mock_ext_device_repo, mock_users_repo, mock_ext_data_repo)
        assert service._ext_device is mock_ext_device_repo
        assert service._users is mock_users_repo
        assert service._ext_data is mock_ext_data_repo


class TestExtDeviceServiceProcessPingRequest:
    @pytest.mark.asyncio
    async def test_process_ping_request_creates_new_device(self):
        mock_events = MagicMock()
        mock_events.broadcast_private = AsyncMock()
        mock_events.broadcast_public = AsyncMock()
        mock_ext_device_repo = MagicMock()
        mock_ext_device_repo.get_ext_device = AsyncMock(return_value=None)
        mock_ext_device_repo.add_device = AsyncMock()
        mock_users_repo = MagicMock()
        mock_ext_data_repo = MagicMock()
        mock_ext_data_repo.get_last_ext_data_by_user_id = AsyncMock(return_value=None)
        mock_ext_data_repo.add_ext_data = AsyncMock()

        user = User(name="testuser", password="hashed", is_active=True, is_reporter=False)
        mock_users_repo.get_user = AsyncMock(return_value=user)

        service = ExtDeviceService(mock_events, mock_ext_device_repo, mock_users_repo, mock_ext_data_repo)
        ping_request = DevicePingRequest(
            macAddress="00:11:22:33:44:55",
            fwVersion="1.0.0",
            fsVersion="2.0.0",
            uptime=3600,
        )
        result = await service.process_ping_request(ping_request, "testuser")
        assert result is None  # Returns None on success
        mock_ext_device_repo.add_device.assert_called_once()
        mock_events.broadcast_private.assert_called_once_with("ext_device_updated")

    @pytest.mark.asyncio
    async def test_process_ping_request_updates_existing_device(self):
        mock_events = MagicMock()
        mock_events.broadcast_private = AsyncMock()
        mock_events.broadcast_public = AsyncMock()
        mock_ext_device_repo = MagicMock()
        mock_users_repo = MagicMock()
        mock_ext_data_repo = MagicMock()
        mock_ext_data_repo.get_last_ext_data_by_user_id = AsyncMock(return_value=None)
        mock_ext_data_repo.add_ext_data = AsyncMock()

        user = User(name="testuser", password="hashed", is_active=True, is_reporter=False)
        mock_users_repo.get_user = AsyncMock(return_value=user)

        existing_device = ExtDevice(
            mac_address="00:11:22:33:44:55",
            fw_version="0.9.0",
            fs_version="1.0.0",
            uptime=100,
        )
        mock_ext_device_repo.get_ext_device = AsyncMock(return_value=existing_device)
        mock_ext_device_repo.update_device = AsyncMock()

        service = ExtDeviceService(mock_events, mock_ext_device_repo, mock_users_repo, mock_ext_data_repo)
        ping_request = DevicePingRequest(
            macAddress="00:11:22:33:44:55",
            fwVersion="1.0.0",
            fsVersion="2.0.0",
            uptime=3600,
        )
        await service.process_ping_request(ping_request, "testuser")
        mock_ext_device_repo.update_device.assert_called_once()
        assert existing_device.fw_version == "1.0.0"

    @pytest.mark.asyncio
    async def test_process_ping_request_user_not_found(self):
        mock_events = MagicMock()
        mock_ext_device_repo = MagicMock()
        mock_users_repo = MagicMock()
        mock_ext_data_repo = MagicMock()

        mock_users_repo.get_user = AsyncMock(return_value=None)

        service = ExtDeviceService(mock_events, mock_ext_device_repo, mock_users_repo, mock_ext_data_repo)
        ping_request = DevicePingRequest(
            macAddress="00:11:22:33:44:55",
            fwVersion="1.0.0",
            fsVersion="2.0.0",
            uptime=3600,
        )
        result = await service.process_ping_request(ping_request, "nonexistent")
        assert result is None
        mock_ext_device_repo.get_ext_device.assert_not_called()


class TestExtDeviceServiceGetAllDevices:
    @pytest.mark.asyncio
    async def test_get_all_devices_returns_response_list(self):
        mock_events = MagicMock()
        mock_ext_device_repo = MagicMock()
        mock_users_repo = MagicMock()
        mock_ext_data_repo = MagicMock()

        user = User(name="testuser", password="hashed", is_active=True, is_reporter=False)
        device = ExtDevice(
            mac_address="00:11:22:33:44:55",
            fw_version="1.0.0",
            fs_version="2.0.0",
            uptime=3600,
            user=user,
        )
        mock_ext_device_repo.get_all_devices = AsyncMock(return_value=[device])
        mock_ext_data_repo.get_last_ext_data_by_user_id = AsyncMock(return_value=None)

        service = ExtDeviceService(mock_events, mock_ext_device_repo, mock_users_repo, mock_ext_data_repo)
        result = await service.get_all_devices()
        assert len(result) == 1
        assert isinstance(result[0], ExtDeviceResponse)
        assert result[0].mac_address == "00:11:22:33:44:55"

    @pytest.mark.asyncio
    async def test_get_all_devices_empty_list(self):
        mock_events = MagicMock()
        mock_ext_device_repo = MagicMock()
        mock_users_repo = MagicMock()
        mock_ext_data_repo = MagicMock()

        mock_ext_device_repo.get_all_devices = AsyncMock(return_value=[])

        service = ExtDeviceService(mock_events, mock_ext_device_repo, mock_users_repo, mock_ext_data_repo)
        result = await service.get_all_devices()
        assert result == []

    @pytest.mark.asyncio
    async def test_get_all_devices_with_user_and_grid_state(self):
        """Test get_all_devices with user and grid_state."""
        mock_events = MagicMock()
        mock_ext_device_repo = MagicMock()
        mock_users_repo = MagicMock()
        mock_ext_data_repo = MagicMock()

        user = User(name="testuser", password="hashed", is_active=True, is_reporter=False)
        device = ExtDevice(
            mac_address="00:11:22:33:44:55",
            fw_version="1.0.0",
            fs_version="2.0.0",
            uptime=3600,
            user=user,
        )
        mock_ext_device_repo.get_all_devices = AsyncMock(return_value=[device])

        ext_data = ExtData(user_id=user.id, grid_state=True, received_at=datetime.now(timezone.utc))
        mock_ext_data_repo.get_last_ext_data_by_user_id = AsyncMock(return_value=ext_data)

        service = ExtDeviceService(mock_events, mock_ext_device_repo, mock_users_repo, mock_ext_data_repo)
        result = await service.get_all_devices()
        assert len(result) == 1
        assert result[0].grid_state is True
        assert result[0].user_id == user.id

    @pytest.mark.asyncio
    async def test_get_all_devices_without_user(self):
        """Test get_all_devices with device without user."""
        mock_events = MagicMock()
        mock_ext_device_repo = MagicMock()
        mock_users_repo = MagicMock()
        mock_ext_data_repo = MagicMock()

        # Use a mock device with user=None to avoid Beanie Link validation issues
        device = MagicMock()
        device.mac_address = "00:11:22:33:44:55"
        device.fw_version = "1.0.0"
        device.fs_version = "2.0.0"
        device.uptime = 3600
        device.updated_at = datetime.now(timezone.utc)
        device.user = None

        mock_ext_device_repo.get_all_devices = AsyncMock(return_value=[device])

        service = ExtDeviceService(mock_events, mock_ext_device_repo, mock_users_repo, mock_ext_data_repo)
        result = await service.get_all_devices()
        assert len(result) == 1
        assert result[0].user_id is None
        assert result[0].grid_state is None


class TestExtDeviceServiceUpdateGridState:
    @pytest.mark.asyncio
    async def test_update_grid_state_active_true_no_last_data(self):
        """Test _update_grid_state with active=True and no last_data."""
        mock_events = MagicMock()
        mock_events.broadcast_public = AsyncMock()
        mock_ext_device_repo = MagicMock()
        mock_users_repo = MagicMock()
        mock_ext_data_repo = MagicMock()
        mock_ext_data_repo.get_last_ext_data_by_user_id = AsyncMock(return_value=None)
        mock_ext_data_repo.add_ext_data = AsyncMock()

        service = ExtDeviceService(mock_events, mock_ext_device_repo, mock_users_repo, mock_ext_data_repo)
        await service._update_grid_state(PydanticObjectId(), active=True, now=datetime.now(timezone.utc))
        mock_ext_data_repo.add_ext_data.assert_called_once()
        mock_events.broadcast_public.assert_called_once_with("ext_data_updated")

    @pytest.mark.asyncio
    async def test_update_grid_state_active_true_last_data_false(self):
        """Test _update_grid_state with active=True and last_data.grid_state=False."""
        mock_events = MagicMock()
        mock_events.broadcast_public = AsyncMock()
        mock_ext_device_repo = MagicMock()
        mock_users_repo = MagicMock()
        mock_ext_data_repo = MagicMock()
        mock_ext_data_repo.get_last_ext_data_by_user_id = AsyncMock(
            return_value=ExtData(user_id=PydanticObjectId(), grid_state=False)
        )
        mock_ext_data_repo.add_ext_data = AsyncMock()

        service = ExtDeviceService(mock_events, mock_ext_device_repo, mock_users_repo, mock_ext_data_repo)
        await service._update_grid_state(PydanticObjectId(), active=True, now=datetime.now(timezone.utc))
        mock_ext_data_repo.add_ext_data.assert_called_once()
        mock_events.broadcast_public.assert_called_once_with("ext_data_updated")

    @pytest.mark.asyncio
    async def test_update_grid_state_active_false_last_data_true(self):
        """Test _update_grid_state with active=False and last_data.grid_state=True."""
        mock_events = MagicMock()
        mock_events.broadcast_public = AsyncMock()
        mock_ext_device_repo = MagicMock()
        mock_users_repo = MagicMock()
        mock_ext_data_repo = MagicMock()
        mock_ext_data_repo.get_last_ext_data_by_user_id = AsyncMock(
            return_value=ExtData(user_id=PydanticObjectId(), grid_state=True)
        )
        mock_ext_data_repo.add_ext_data = AsyncMock()

        service = ExtDeviceService(mock_events, mock_ext_device_repo, mock_users_repo, mock_ext_data_repo)
        await service._update_grid_state(PydanticObjectId(), active=False, now=datetime.now(timezone.utc))
        mock_ext_data_repo.add_ext_data.assert_called_once()
        mock_events.broadcast_public.assert_called_once_with("ext_data_updated")

    @pytest.mark.asyncio
    async def test_update_grid_state_no_change(self):
        """Test _update_grid_state when no change needed."""
        mock_events = MagicMock()
        mock_events.broadcast_public = AsyncMock()
        mock_ext_device_repo = MagicMock()
        mock_users_repo = MagicMock()
        mock_ext_data_repo = MagicMock()
        mock_ext_data_repo.get_last_ext_data_by_user_id = AsyncMock(
            return_value=ExtData(user_id=PydanticObjectId(), grid_state=True)
        )

        service = ExtDeviceService(mock_events, mock_ext_device_repo, mock_users_repo, mock_ext_data_repo)
        await service._update_grid_state(PydanticObjectId(), active=True, now=datetime.now(timezone.utc))
        mock_ext_data_repo.add_ext_data.assert_not_called()
        mock_events.broadcast_public.assert_not_called()


class TestExtDeviceServiceCheckPings:
    @pytest.mark.asyncio
    async def test_check_pings_no_devices(self):
        mock_events = MagicMock()
        mock_events.broadcast_public = AsyncMock()
        mock_ext_device_repo = MagicMock()
        mock_users_repo = MagicMock()
        mock_ext_data_repo = MagicMock()

        mock_ext_device_repo.get_all_devices = AsyncMock(return_value=[])

        service = ExtDeviceService(mock_events, mock_ext_device_repo, mock_users_repo, mock_ext_data_repo)
        await service.check_pings()
        mock_ext_data_repo.add_ext_data.assert_not_called()

    @pytest.mark.asyncio
    async def test_check_pings_with_active_device(self):
        mock_events = MagicMock()
        mock_events.broadcast_public = AsyncMock()
        mock_ext_device_repo = MagicMock()
        mock_users_repo = MagicMock()
        mock_ext_data_repo = MagicMock()

        user = User(name="testuser", password="hashed", is_active=True, is_reporter=False)
        device = ExtDevice(
            mac_address="00:11:22:33:44:55",
            fw_version="1.0.0",
            fs_version="2.0.0",
            uptime=3600,
            updated_at=datetime.now(timezone.utc),
            user=user,
        )
        mock_ext_device_repo.get_all_devices = AsyncMock(return_value=[device])
        mock_ext_data_repo.get_last_ext_data_by_user_id = AsyncMock(return_value=None)
        mock_ext_data_repo.add_ext_data = AsyncMock()

        service = ExtDeviceService(mock_events, mock_ext_device_repo, mock_users_repo, mock_ext_data_repo)
        await service.check_pings()
        mock_ext_data_repo.add_ext_data.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_pings_with_inactive_device(self):
        mock_events = MagicMock()
        mock_events.broadcast_public = AsyncMock()
        mock_ext_device_repo = MagicMock()
        mock_users_repo = MagicMock()
        mock_ext_data_repo = MagicMock()

        user = User(name="testuser", password="hashed", is_active=True, is_reporter=False)
        device = ExtDevice(
            mac_address="00:11:22:33:44:55",
            fw_version="1.0.0",
            fs_version="2.0.0",
            uptime=3600,
            updated_at=datetime.now(timezone.utc) - timedelta(minutes=5),
            user=user,
        )
        mock_ext_device_repo.get_all_devices = AsyncMock(return_value=[device])
        mock_ext_data_repo.get_last_ext_data_by_user_id = AsyncMock(
            return_value=ExtData(user_id=user.id, grid_state=True)
        )
        mock_ext_data_repo.add_ext_data = AsyncMock()

        service = ExtDeviceService(mock_events, mock_ext_device_repo, mock_users_repo, mock_ext_data_repo)
        await service.check_pings()
        mock_ext_data_repo.add_ext_data.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_pings_device_without_user(self):
        mock_events = MagicMock()
        mock_events.broadcast_public = AsyncMock()
        mock_ext_device_repo = MagicMock()
        mock_users_repo = MagicMock()
        mock_ext_data_repo = MagicMock()

        # Use a mock device with user=None to avoid Beanie Link validation issues
        device = MagicMock()
        device.mac_address = "00:11:22:33:44:55"
        device.fw_version = "1.0.0"
        device.fs_version = "2.0.0"
        device.uptime = 3600
        device.updated_at = datetime.now(timezone.utc)
        device.user = None

        mock_ext_device_repo.get_all_devices = AsyncMock(return_value=[device])

        service = ExtDeviceService(mock_events, mock_ext_device_repo, mock_users_repo, mock_ext_data_repo)
        await service.check_pings()
        mock_ext_data_repo.add_ext_data.assert_not_called()

    @pytest.mark.asyncio
    async def test_check_pings_device_with_naive_datetime(self):
        """Test check_pings handles naive datetime (tzinfo is None)."""
        mock_events = MagicMock()
        mock_events.broadcast_public = AsyncMock()
        mock_ext_device_repo = MagicMock()
        mock_users_repo = MagicMock()
        mock_ext_data_repo = MagicMock()

        user = User(name="testuser", password="hashed", is_active=True, is_reporter=False)
        # Create a naive datetime (no timezone info)
        naive_dt = datetime.now()  # This has no tzinfo
        device = ExtDevice(
            mac_address="00:11:22:33:44:55",
            fw_version="1.0.0",
            fs_version="2.0.0",
            uptime=3600,
            user=user,
            updated_at=naive_dt,
        )
        mock_ext_device_repo.get_all_devices = AsyncMock(return_value=[device])
        mock_ext_data_repo.get_last_ext_data_by_user_id = AsyncMock(return_value=None)
        mock_ext_data_repo.add_ext_data = AsyncMock()

        service = ExtDeviceService(mock_events, mock_ext_device_repo, mock_users_repo, mock_ext_data_repo)
        await service.check_pings()
        mock_ext_data_repo.add_ext_data.assert_called_once()