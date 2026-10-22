from datetime import datetime
from typing import Any
from beanie import PydanticObjectId
from pydantic import BaseModel, Field

from shared.models.push_delivery import PushDeliveryStatus


_CONFIG = {
    "populate_by_name": True,
    "from_attributes": True,
}


class PushTemplateParamResponse(BaseModel):
    key: str
    value: int
    default: int
    min: int
    max: int


class PushTemplateResponse(BaseModel):
    topic: str
    enabled: bool
    title: dict[str, str]
    body: dict[str, str]
    route: str
    should_send: str | None = Field(None, alias="shouldSend")
    macros: str | None = None
    params: list[PushTemplateParamResponse]
    # Sample variables of the event, used by the preview and editor autocompletion
    variables: dict[str, Any]
    updated_at: datetime = Field(alias="updatedAt")

    model_config = _CONFIG


class PushTemplateRequest(BaseModel):
    enabled: bool = True
    title: dict[str, str]
    body: dict[str, str]
    route: str = ""
    should_send: str | None = Field(None, alias="shouldSend")
    macros: str | None = None
    params: dict[str, int] = Field(default_factory=dict)

    model_config = _CONFIG


class PushTemplateTestRequest(PushTemplateRequest):
    device_id: PydanticObjectId = Field(alias="deviceId")


class PushTemplatePreviewItem(BaseModel):
    language: str
    title: str | None = None
    body: str | None = None
    route: str | None = None
    error: str | None = None


class PushTemplatePreviewResponse(BaseModel):
    should_send: bool | None = Field(None, alias="shouldSend")
    should_send_error: str | None = Field(None, alias="shouldSendError")
    items: list[PushTemplatePreviewItem]

    model_config = _CONFIG


class PushDeliveryResponse(BaseModel):
    id: PydanticObjectId
    dedup_key: str = Field(alias="dedupKey")
    topic: str
    summary: dict[str, str]
    building_id: PydanticObjectId | None = Field(None, alias="buildingId")
    status: PushDeliveryStatus
    recipients: int
    recipients_by_language: dict[str, int] = Field(alias="recipientsByLanguage")
    success_count: int = Field(alias="successCount")
    failure_count: int = Field(alias="failureCount")
    invalid_removed: int = Field(alias="invalidRemoved")
    created_at: datetime = Field(alias="createdAt")
    error: str | None = None

    model_config = _CONFIG


class AnnouncementRequest(BaseModel):
    title: dict[str, str]
    body: dict[str, str]


class AnnouncementResponse(BaseModel):
    id: PydanticObjectId
    title: dict[str, str]
    body: dict[str, str]
    created_at: datetime = Field(alias="createdAt")
    delivery: PushDeliveryResponse | None = None

    model_config = _CONFIG


__all__ = [
    "AnnouncementRequest",
    "AnnouncementResponse",
    "PushTemplateParamResponse",
    "PushTemplateResponse",
    "PushTemplateRequest",
    "PushTemplateTestRequest",
    "PushTemplatePreviewItem",
    "PushTemplatePreviewResponse",
    "PushDeliveryResponse",
]
