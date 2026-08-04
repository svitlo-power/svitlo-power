from typing import Optional
from beanie import PydanticObjectId
from pydantic import BaseModel, Field


class UpdateDeyeConnectionRequest(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    base_url: str = Field(alias="baseUrl", min_length=1, max_length=256)
    app_id: str = Field(alias="appId", min_length=1, max_length=128)
    # Empty/absent secrets mean "keep the stored value" on update
    app_secret: Optional[str] = Field(None, alias="appSecret")
    email: str = Field(min_length=1, max_length=256)
    password: Optional[str] = None
    sync_stations_on_poll: bool = Field(False, alias="syncStationsOnPoll")

    model_config = {
        "populate_by_name": True,
        "from_attributes": True,
    }


class CreateDeyeConnectionRequest(UpdateDeyeConnectionRequest):
    app_secret: str = Field(alias="appSecret", min_length=1)
    password: str = Field(min_length=1)


class DeyeConnectionResponse(BaseModel):
    id: PydanticObjectId
    name: str
    base_url: str = Field(alias="baseUrl")
    app_id: str = Field(alias="appId")
    email: str
    sync_stations_on_poll: bool = Field(alias="syncStationsOnPoll")

    model_config = {
        "populate_by_name": True,
        "from_attributes": True,
    }


class DeyeConnectionDefaultsResponse(BaseModel):
    base_url: Optional[str] = Field(None, alias="baseUrl")

    model_config = {
        "populate_by_name": True,
    }


__all__ = [
    "CreateDeyeConnectionRequest",
    "UpdateDeyeConnectionRequest",
    "DeyeConnectionResponse",
    "DeyeConnectionDefaultsResponse",
]
