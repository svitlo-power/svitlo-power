from beanie import PydanticObjectId
from beanie.operators import In
from pydantic import BaseModel
from shared.models.push_device import PushDevice
from shared.repositories.interfaces.push_devices import IPushDevicesRepository, PushRecipient


class _DeviceToken(BaseModel):
    token: str


class _DeviceRecipient(BaseModel):
    token: str
    language: str = "uk"


class PushDevicesRepository(IPushDevicesRepository):

    async def get_device(self, token: str) -> PushDevice | None:
        return await PushDevice.find_one(PushDevice.token == token)

    async def get_device_by_id(self, device_id: PydanticObjectId) -> PushDevice | None:
        return await PushDevice.get(device_id)

    async def save_device(self, device: PushDevice) -> PushDevice:
        await device.save()
        return device

    async def delete_device(self, token: str) -> bool:
        result = await PushDevice.find(PushDevice.token == token).delete()
        return bool(result and result.deleted_count)

    async def delete_device_by_id(self, device_id: PydanticObjectId) -> bool:
        result = await PushDevice.find(PushDevice.id == device_id).delete()
        return bool(result and result.deleted_count)

    async def delete_devices(self, tokens: list[str]) -> int:
        if not tokens:
            return 0
        result = await PushDevice.find(In(PushDevice.token, tokens)).delete()
        return result.deleted_count if result else 0

    @staticmethod
    async def _find_tokens(query) -> list[str]:
        # Sending needs only the tokens, so the rest of the document is not loaded
        devices = await PushDevice.find(query).project(_DeviceToken).to_list()
        return [d.token for d in devices]

    async def get_enabled_tokens(self) -> list[str]:
        return await self._find_tokens(PushDevice.enabled == True)

    @staticmethod
    def _topic_query(topic: str) -> dict:
        # $ne on an array field matches documents where no element equals the value
        return { "enabled": True, "disabled_topics": { "$ne": topic } }

    async def get_topic_tokens(self, topic: str) -> list[str]:
        return await self._find_tokens(self._topic_query(topic))

    async def get_topic_recipients(self, topic: str) -> list[PushRecipient]:
        devices = await PushDevice.find(self._topic_query(topic)).project(_DeviceRecipient).to_list()
        return [PushRecipient(token=d.token, language=d.language) for d in devices]

    async def count_topic_devices(self, topic: str) -> int:
        return await PushDevice.find(self._topic_query(topic)).count()

    async def get_all_devices(self) -> list[PushDevice]:
        return await PushDevice.find_all().sort(-PushDevice.last_seen).to_list()
