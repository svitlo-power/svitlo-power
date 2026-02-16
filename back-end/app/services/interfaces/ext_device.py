from abc import ABC, abstractmethod

from app.models.api import DevicePingRequest, ExtDeviceResponse


class IExtDeviceService(ABC):
    
    @abstractmethod
    async def process_ping_request(
        self,
        ping_request: DevicePingRequest,
        user_name: str,
    ):
        ...

    @abstractmethod
    async def get_all_devices(self) -> list[ExtDeviceResponse]:
        ...

    @abstractmethod
    async def check_pings(self):
        ...