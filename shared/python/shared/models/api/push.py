from datetime import datetime
from beanie import PydanticObjectId
from pydantic import BaseModel, Field

from shared.models.push_device import PushPlatform


class PushDeviceRegisterRequest(BaseModel):
    token: str = Field(min_length=1, max_length=4096)
    platform: PushPlatform
    language: str = "uk"
    app_version: str | None = Field(None, alias="appVersion")

    model_config = {
        "populate_by_name": True,
    }


class PushDeviceTokenRequest(BaseModel):
    token: str = Field(min_length=1, max_length=4096)


class PushDeviceSubscriptionsRequest(BaseModel):
    token: str = Field(min_length=1, max_length=4096)
    enabled: bool = True
    disabled_topics: list[str] = Field(default_factory=list, alias="disabledTopics")
    buildings: list[PydanticObjectId] = Field(default_factory=list)

    model_config = {
        "populate_by_name": True,
    }


class PushDeviceResponse(BaseModel):
    id: PydanticObjectId
    platform: PushPlatform
    language: str
    enabled: bool
    disabled_topics: list[str] = Field(alias="disabledTopics")
    buildings: list[PydanticObjectId]
    app_version: str | None = Field(None, alias="appVersion")
    created_at: datetime = Field(alias="createdAt")
    last_seen: datetime = Field(alias="lastSeen")

    model_config = {
        "populate_by_name": True,
        "from_attributes": True,
    }


class PushTestRequest(BaseModel):
    title: str = Field(min_length=1)
    body: str = Field(min_length=1)
    device_id: PydanticObjectId | None = Field(None, alias="deviceId")
    topic: str | None = None
    route: str | None = None

    model_config = {
        "populate_by_name": True,
    }


class PushSendResult(BaseModel):
    success_count: int = Field(alias="successCount")
    failure_count: int = Field(alias="failureCount")
    removed_count: int = Field(alias="removedCount")

    model_config = {
        "populate_by_name": True,
    }


class PushTopicResponse(BaseModel):
    key: str
    name: dict[str, str]
    description: dict[str, str]


class PushTopicAdminResponse(PushTopicResponse):
    enabled: bool
    order: int
    subscribers: int


class PushTopicStateRequest(BaseModel):
    enabled: bool


__all__ = [
    "PushDeviceRegisterRequest",
    "PushDeviceTokenRequest",
    "PushDeviceSubscriptionsRequest",
    "PushDeviceResponse",
    "PushTestRequest",
    "PushSendResult",
    "PushTopicResponse",
    "PushTopicAdminResponse",
    "PushTopicStateRequest",
]
