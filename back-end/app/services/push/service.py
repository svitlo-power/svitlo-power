from datetime import datetime, timezone
import logging
from beanie import PydanticObjectId
from injector import inject

from shared.models.localizable_value import LocalizableValue
from shared.models.push_device import PushDevice
from shared.models.push_topic import PushTopic
from app.repositories import IPushDevicesRepository, IPushTopicsRepository
from app.models.api import (
    PushDeviceRegisterRequest,
    PushDeviceSubscriptionsRequest,
    PushDeviceResponse,
    PushSendResult,
    PushTopicResponse,
    PushTopicAdminResponse,
)
from .fcm_sender import FcmSender, PushMessage
from .topics import DEFAULT_TOPICS


logger = logging.getLogger(__name__)


@inject
class PushService:
    def __init__(
        self,
        devices: IPushDevicesRepository,
        topics: IPushTopicsRepository,
        sender: FcmSender,
    ):
        self._devices = devices
        self._topics = topics
        self._sender = sender


    async def register_device(self, request: PushDeviceRegisterRequest) -> PushDeviceResponse:
        now = datetime.now(timezone.utc)
        device = await self._devices.get_device(request.token)

        if not device:
            device = PushDevice(
                token       = request.token,
                platform    = request.platform,
                created_at  = now,
            )

        device.platform = request.platform
        device.language = request.language
        device.app_version = request.app_version
        device.last_seen = now

        device = await self._devices.save_device(device)
        return PushDeviceResponse.model_validate(device)


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


    async def delete_device(self, device_id: PydanticObjectId) -> bool:
        return await self._devices.delete_device_by_id(device_id)


    async def get_all_devices(self) -> list[PushDeviceResponse]:
        devices = await self._devices.get_all_devices()
        return [PushDeviceResponse.model_validate(d) for d in devices]


    async def send_to_tokens(self, tokens: list[str], message: PushMessage) -> PushSendResult:
        result = await self._sender.send(tokens, message)

        removed = await self._devices.delete_devices(result.invalid_tokens)
        if removed:
            logger.info(f"Removed {removed} unregistered push devices")

        return PushSendResult(
            success_count   = result.success_count,
            failure_count   = result.failure_count,
            removed_count   = removed,
        )


    async def send_to_device(self, device_id: PydanticObjectId, message: PushMessage) -> PushSendResult | None:
        device = await self._devices.get_device_by_id(device_id)
        if not device:
            return None
        return await self.send_to_tokens([device.token], message)


    async def send_to_all(self, message: PushMessage) -> PushSendResult:
        devices = await self._devices.get_enabled_devices()
        return await self.send_to_tokens([d.token for d in devices], message)


    async def send_to_topic(self, key: str, message: PushMessage) -> PushSendResult | None:
        """Sends to devices subscribed to the topic; nothing is sent while the topic is turned off."""
        topic = await self._topics.get_topic(key)
        if not topic:
            return None
        if not topic.enabled:
            return PushSendResult(success_count=0, failure_count=0, removed_count=0)

        devices = await self._devices.get_topic_devices(key)
        message.data = { **message.data, "topic": key }
        return await self.send_to_tokens([d.token for d in devices], message)


    # -------------------------
    # Topics
    # -------------------------

    async def ensure_default_topics(self):
        """Creates missing built-in topics; existing ones keep their state."""
        existing = { t.key for t in await self._topics.get_all_topics() }
        for order, definition in enumerate(DEFAULT_TOPICS):
            if definition.key in existing:
                continue
            await self._topics.add_topic(PushTopic(
                key         = definition.key,
                name        = LocalizableValue(definition.name),
                description = LocalizableValue(definition.description),
                order       = order,
            ))
            logger.info(f"Created push topic {definition.key}")


    async def get_enabled_topics(self) -> list[PushTopicResponse]:
        topics = await self._topics.get_enabled_topics()
        return [
            PushTopicResponse(key=t.key, name=t.name.root, description=t.description.root)
            for t in topics
        ]


    async def get_all_topics(self) -> list[PushTopicAdminResponse]:
        topics = await self._topics.get_all_topics()
        return [
            PushTopicAdminResponse(
                key         = t.key,
                name        = t.name.root,
                description = t.description.root,
                enabled     = t.enabled,
                order       = t.order,
                subscribers = await self._devices.count_topic_devices(t.key),
            )
            for t in topics
        ]


    async def set_topic_state(self, key: str, enabled: bool) -> bool:
        return await self._topics.set_enabled(key, enabled)
