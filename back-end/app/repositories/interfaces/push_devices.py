from abc import ABC, abstractmethod
from beanie import PydanticObjectId

from shared.models.push_device import PushDevice


class IPushDevicesRepository(ABC):
    @abstractmethod
    async def get_device(self, token: str) -> PushDevice | None:
        ...

    @abstractmethod
    async def get_device_by_id(self, device_id: PydanticObjectId) -> PushDevice | None:
        ...

    @abstractmethod
    async def save_device(self, device: PushDevice) -> PushDevice:
        ...

    @abstractmethod
    async def delete_device(self, token: str) -> bool:
        ...

    @abstractmethod
    async def delete_device_by_id(self, device_id: PydanticObjectId) -> bool:
        ...

    @abstractmethod
    async def delete_devices(self, tokens: list[str]) -> int:
        ...

    @abstractmethod
    async def get_enabled_devices(self) -> list[PushDevice]:
        ...

    @abstractmethod
    async def get_topic_devices(self, topic: str) -> list[PushDevice]:
        ...

    @abstractmethod
    async def count_topic_devices(self, topic: str) -> int:
        ...

    @abstractmethod
    async def get_all_devices(self) -> list[PushDevice]:
        ...
