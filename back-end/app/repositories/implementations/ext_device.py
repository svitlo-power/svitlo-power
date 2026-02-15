from beanie import PydanticObjectId
from shared.models.ext_device import ExtDevice
from ..interfaces.ext_device import IExtDeviceRepository

class ExtDeviceRepository(IExtDeviceRepository):

    async def get_ext_device(self, mac_address: str) -> ExtDevice:
        return await ExtDevice.find_one(ExtDevice.mac_address == mac_address)

    async def add_device(self, device: ExtDevice) -> PydanticObjectId:
        await device.insert()
        return device.id

    async def update_device(self, device: ExtDevice) -> PydanticObjectId:
        await device.save()
        return device.id