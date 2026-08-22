import logging
from typing import List
from beanie import PydanticObjectId
from fastapi import FastAPI, Depends, HTTPException, Body
from fastapi_injector import Injected

from app.models.api import (
    MessageListResponseModel,
    MessageEditResponseModel,
    MessageUpdateRequest,
    MessageCreateRequest,
    MessagePreviewRequest,
    MessagePreviewResponse,
    SaveMessageStateRequest,
)
from app.services import (
    MessagesService,
    TelegramService,
)
from app.utils.jwt_dependencies import jwt_required


logger = logging.getLogger(__name__)


def register(app: FastAPI):

    def _get_channel_name(telegram: TelegramService, channel_id: str, bot_id: str):
        try:
            chat_info = telegram.get_chat_info(channel_id, bot_id)
            return chat_info.title
        except Exception as e:
            logger.error(f'Cannot get channel info for channel {channel_id}: {str(e)}')
            return 'Invalid channel identifier'


    @app.get("/api/messages/messages")
    async def get_messages(
        _ = Depends(jwt_required),
        messages = Injected(MessagesService)
    ) -> List[MessageListResponseModel]:
        return await messages.get_messages(all=True)


    @app.post("/api/messages/getChannel")
    def get_channel(
        channel_id: str = Body(..., alias="channelId"), 
        bot_id: PydanticObjectId = Body(..., alias="botId"), 
        _ = Depends(jwt_required),
        telegram = Injected(TelegramService)
    ):
        if not channel_id or not bot_id:
            raise HTTPException(status_code=400, detail="channelId and botId should be specified")
        channel_name = _get_channel_name(telegram, channel_id, bot_id)
        return { 'success': True, 'channelName': channel_name }


    @app.get("/api/messages/message/{message_id}")
    async def get_message(
        message_id: PydanticObjectId,
        _ = Depends(jwt_required),
        messages = Injected(MessagesService)
    ) -> MessageEditResponseModel:
        return await messages.get_message(message_id)


    @app.post("/api/messages/getPreview")
    async def get_message_preview(
        body: MessagePreviewRequest,
        _ = Depends(jwt_required),
        messages = Injected(MessagesService)
    ) -> MessagePreviewResponse:
        try:
            return await messages.get_message_preview(body)
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))


    @app.patch("/api/messages/{message_id}/state")
    async def save_message_state(
        message_id: PydanticObjectId,
        body: SaveMessageStateRequest,
        _ = Depends(jwt_required),
        messages = Injected(MessagesService),
    ):
        await messages.save_state(message_id, body.enabled)
        return { 'success': True, 'id': str(message_id) }


    @app.post("/api/messages")
    async def create_message(
        body: MessageCreateRequest,
        _ = Depends(jwt_required),
        messages = Injected(MessagesService),
    ):
        return await messages.create_message(body)


    @app.put("/api/messages/{message_id}")
    async def update_message(
        message_id: PydanticObjectId,
        body: MessageUpdateRequest,
        _ = Depends(jwt_required),
        messages = Injected(MessagesService),
    ):
        return await messages.update_message(message_id, body)
