from datetime import datetime
from beanie import PydanticObjectId
from pydantic import BaseModel, Field


class DevicePingRequest(BaseModel):
    mac_address: str = Field(alias="macAddress")
    fw_version: str = Field(alias="fwVersion")
    fs_version: str = Field(alias="fsVersion")
    uptime: int

    model_config = {
        "populate_by_name": True,
        "from_attributes": True,
    }


class ExtDeviceResponse(BaseModel):
    mac_address: str = Field(alias="macAddress")
    fw_version: str = Field(alias="fwVersion")
    fs_version: str = Field(alias="fsVersion")
    uptime: int
    updated_at: datetime = Field(alias="updatedAt")
    user_id: PydanticObjectId | None = Field(None, alias="userId")
    grid_state: bool | None = Field(None, alias="gridState")

    model_config = {
        "populate_by_name": True,
        "from_attributes": True,
    }

__all__ = [
    "DevicePingRequest",
    "ExtDeviceResponse",
]