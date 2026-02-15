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

__all__ = [
    "DevicePingRequest",
]