from abc import ABC, abstractmethod
from beanie import PydanticObjectId

from shared.models.ext_device import ExtDevice


class IExtDeviceRepository(ABC):
    @abstractmethod
    async def get_ext_device(self, mac_address: str) -> ExtDevice:
        ...

    @abstractmethod
    async def add_device(self, device: ExtDevice) -> PydanticObjectId:
        ...

    @abstractmethod
    async def update_device(self, device: ExtDevice) -> PydanticObjectId:
        ...

    @abstractmethod
    async def get_all_devices(self) -> list[ExtDevice]:
        ...