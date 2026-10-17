from datetime import datetime, timezone
from injector import inject
from pymongo.errors import DuplicateKeyError

from shared.models.push_device import PushDevice
from shared.models.api.push import (
    PushDeviceRegisterRequest,
    PushDeviceSubscriptionsRequest,
    PushDeviceResponse,
    PushTopicResponse,
)
from shared.repositories.interfaces.push_devices import IPushDevicesRepository
from shared.repositories.interfaces.push_topics import IPushTopicsRepository


@inject
class PushDevicesService:
    """Device registration and subscriptions for anonymous app devices.

    Used by both backends; sending and admin operations are in the full PushService
    in the back-end app.
    """
    def __init__(
        self,
        devices: IPushDevicesRepository,
        topics: IPushTopicsRepository,
    ):
        self._devices = devices
        self._topics = topics


    async def register_device(self, request: PushDeviceRegisterRequest) -> PushDeviceResponse:
        now = datetime.now(timezone.utc)
        device = await self._devices.get_device(request.token)

        if not device:
            device = PushDevice(
                token       = request.token,
                platform    = request.platform,
                created_at  = now,
            )

        try:
            device = await self._save_registration(device, request, now)
        except DuplicateKeyError:
            # A concurrent request inserted the same token first; update that record instead
            device = await self._devices.get_device(request.token)
            if not device:
                raise
            device = await self._save_registration(device, request, now)

        return PushDeviceResponse.model_validate(device)


    async def _save_registration(
        self,
        device: PushDevice,
        request: PushDeviceRegisterRequest,
        now: datetime,
    ) -> PushDevice:
        device.platform = request.platform
        device.language = request.language
        device.app_version = request.app_version
        device.last_seen = now
        return await self._devices.save_device(device)


    async def update_subscriptions(
        self,
        request: PushDeviceSubscriptionsRequest,
    ) -> PushDeviceResponse | None:
        device = await self._devices.get_device(request.token)
        if not device:
            return None

        device.enabled = request.enabled
        device.disabled_topics = list(dict.fromkeys(request.disabled_topics))
        device.buildings = list(dict.fromkeys(request.buildings))
        device.last_seen = datetime.now(timezone.utc)

        device = await self._devices.save_device(device)
        return PushDeviceResponse.model_validate(device)


    async def get_device(self, token: str) -> PushDeviceResponse | None:
        device = await self._devices.get_device(token)
        return PushDeviceResponse.model_validate(device) if device else None


    async def unregister_device(self, token: str) -> bool:
        return await self._devices.delete_device(token)


    async def get_enabled_topics(self) -> list[PushTopicResponse]:
        topics = await self._topics.get_enabled_topics()
        return [
            PushTopicResponse(key=t.key, name=t.name.root, description=t.description.root)
            for t in topics
        ]
