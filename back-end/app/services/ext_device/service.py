from datetime import datetime, timezone
import logging
from injector import inject

from shared.models.ext_device import ExtDevice

from ..base import BaseService
from app.repositories import IExtDeviceRepository, IUsersRepository
from shared.services.events.service import EventsService
from ..interfaces import IExtDeviceService
from app.models.api import DevicePingRequest


logger = logging.getLogger(__name__)

@inject
class ExtDeviceService(BaseService, IExtDeviceService):
    def __init__(
        self,
        events: EventsService,
        ext_device: IExtDeviceRepository,
        users: IUsersRepository,
    ):
        super().__init__(events)
        self._ext_device = ext_device
        self._users = users

    async def process_ping_request(
        self,
        ping_request: DevicePingRequest,
        user_name: str,
    ):
        user = await self._users.get_user(user_name=user_name)
        if not user:
            logger.error(f"Cannot find user {user_name}")
            return None

        device = await self._ext_device.get_ext_device(ping_request.mac_address)
        if not device:
            device = ExtDevice(
                fw_version  = ping_request.fw_version,
                fs_version  = ping_request.fs_version,
                uptime      = ping_request.uptime,
                mac_address = ping_request.mac_address,
                updated_at  = datetime.now(timezone.utc),
                user        = user,
            )
            await self._ext_device.add_device(device)
        else:
            device.fw_version = ping_request.fw_version
            device.fs_version = ping_request.fs_version
            device.uptime = ping_request.uptime
            device.updated_at = datetime.now(timezone.utc)
            await self._ext_device.update_device(device)
        await self._events.broadcast_private("ext_device_updated")