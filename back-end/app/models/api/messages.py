from datetime import datetime
from typing import List, Any, Optional
from beanie import PydanticObjectId
from pydantic import BaseModel, Field


class MessageListResponseModel(BaseModel):
    id: PydanticObjectId
    name: str
    channel_name: str = Field(alias="channelName")
    stations: List[PydanticObjectId]
    bot_name: str = Field(alias="botName")
    last_sent_time: Optional[datetime] = Field(None, alias="lastSentTime")
    enabled: bool

    model_config = {
        "populate_by_name": True,
        "from_attributes": True,
    }


class MessageEditResponseModel(BaseModel):
    id: PydanticObjectId
    name: str
    channel_id: str = Field(alias="channelId")
    channel_name: str = Field(alias="channelName")
    stations: List[PydanticObjectId]
    bot_id: PydanticObjectId = Field(alias="botId")
    bot_name: str = Field(alias="botName")
    last_sent_time: Optional[datetime] = Field(None, alias="lastSentTime")
    template_macros: Optional[str] = Field(None, alias="templateMacros")
    message_template: str = Field(alias="messageTemplate")
    should_send_template: str = Field(alias="shouldSendTemplate")
    timeout_template: str = Field(alias="timeoutTemplate")
    enabled: bool
    language: str

    model_config = {
        "populate_by_name": True,
        "from_attributes": True,
    }


class MessageCreateRequest(BaseModel):
    name: str
    channel_id: str = Field(alias="channelId")
    stations: List[PydanticObjectId]
    bot_id: PydanticObjectId = Field(alias="botId")
    template_macros: Optional[str] = Field(None, alias="templateMacros")
    message_template: str = Field(alias="messageTemplate")
    should_send_template: str = Field(alias="shouldSendTemplate")
    timeout_template: str = Field(alias="timeoutTemplate")
    enabled: bool
    language: str

    model_config = {
        "populate_by_name": True,
        "from_attributes": True,
    }


class MessageUpdateRequest(MessageCreateRequest):
    model_config = {
        "populate_by_name": True,
        "from_attributes": True,
    }


class MessagePreviewRequest(BaseModel):
    id: Optional[PydanticObjectId] = Field(None)
    name: str
    message_template: str = Field(alias="messageTemplate")
    timeout_template: str = Field(alias="timeoutTemplate")
    should_send_template: Optional[str] = Field(None, alias="shouldSendTemplate")
    template_macros: Optional[str] = Field(None, alias="templateMacros")
    stations: List[PydanticObjectId]
    language: str

    model_config = {
        "populate_by_name": True,
        "from_attributes": True,
    }


class MessagePreviewResponse(BaseModel):
    success: bool
    message: str
    should_send: bool = Field(alias="shouldSend")
    timeout: int
    next_send_time: datetime = Field(alias="nextSendTime")

    model_config = {
        "populate_by_name": True,
        "from_attributes": True,
    }


class SaveMessageStateRequest(BaseModel):
    enabled: bool = False


__all__ = [
    "MessageListResponseModel",
    "MessageEditResponseModel",
    "MessagePreviewRequest",
    "MessagePreviewResponse",
    "SaveMessageStateRequest",
    "MessageCreateRequest",
    "MessageUpdateRequest",
]
