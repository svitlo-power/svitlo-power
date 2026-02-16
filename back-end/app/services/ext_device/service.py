from datetime import datetime, timezone
import logging
from injector import inject

from shared.models.ext_device import ExtDevice

from ..base import BaseService
from app.repositories import IExtDeviceRepository, IUsersRepository, IExtDataRepository
from shared.services.events.service import EventsService
from ..interfaces import IExtDeviceService
from app.models.api import DevicePingRequest, ExtDeviceResponse


logger = logging.getLogger(__name__)

@inject
class ExtDeviceService(BaseService, IExtDeviceService):
    def __init__(
        self,
        events: EventsService,
        ext_device: IExtDeviceRepository,
        users: IUsersRepository,
        ext_data: IExtDataRepository,
    ):
        super().__init__(events)
        self._ext_device = ext_device
        self._users = users
        self._ext_data = ext_data


    async def _update_grid_state(self, user_id, active: bool, date: datetime):
        last_data = await self._ext_data.get_last_ext_data_by_user_id(user_id)

        if active:
            if not last_data or last_data.grid_state == False:
                await self._ext_data.add_ext_data(user_id, grid_state=True, date=date)
                await self._events.broadcast_public("ext_data_updated")
        else:
            if last_data and last_data.grid_state == True:
                await self._ext_data.add_ext_data(user_id, grid_state=False, date=date)
                await self._events.broadcast_public("ext_data_updated")


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

        await self._update_grid_state(user.id, active=True, now=datetime.now(timezone.utc))


    async def get_all_devices(self) -> list[ExtDeviceResponse]:
        devices = await self._ext_device.get_all_devices()
        
        result = []
        for device in devices:
            last_data = await self._ext_data.get_last_ext_data_by_user_id(device.user.id) if device.user else None
            
            result.append(ExtDeviceResponse(
                mac_address = device.mac_address,
                fw_version  = device.fw_version,
                fs_version  = device.fs_version,
                uptime      = device.uptime,
                updated_at  = device.updated_at,
                user_id     = device.user.id if device.user else None,
                grid_state  = last_data.grid_state if last_data else None,
            ))
        
        return result


    async def check_pings(self):
        devices = await self._ext_device.get_all_devices()
        now = datetime.now(timezone.utc)

        user_devices = {}
        for device in devices:
            if not device.user:
                logger.warning(f"Device {device.mac_address} has no user")
                continue

            if device.updated_at and device.updated_at.tzinfo is None:
                device.updated_at = device.updated_at.replace(tzinfo=timezone.utc)

            user_id = device.user.id
            if user_id not in user_devices:
                user_devices[user_id] = []
            user_devices[user_id].append(device)

        for user_id, devices in user_devices.items():
            active = any((now - d.updated_at).total_seconds() < 120 for d in devices)
            await self._update_grid_state(user_id, active, now)
