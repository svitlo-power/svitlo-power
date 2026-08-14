import asyncio
import logging
from typing import List
from beanie import PydanticObjectId
from injector import inject

from app.models.api import ChatIdRequest, AllowedChatResponse, ChatRequestResponse
from app.repositories import IChatsRepository
from shared.models.allowed_chat import AllowedChat
from shared.models.chat_request import ChatRequest
from shared.services.events.service import EventsService
from ..base import BaseService
from ..telegram import TelegramService


logger = logging.getLogger(__name__)


@inject
class ChatsService(BaseService):
    def __init__(
        self,
        chats: IChatsRepository,
        telegram: TelegramService,
        events: EventsService,
    ):
        super().__init__(events)
        self._chats = chats
        self._telegram = telegram

    async def _get_bot_name(self, bot_id: str):
        try:
            bot_info = await self._telegram.get_bot_info(bot_id)
            return bot_info.username
        except:
            logger.error(f"Cannot get bot info for bot {bot_id}")
            return "Invalid bot identifier"

    async def _get_chat_name(self, chat_id: str, bot_id: str):
        try:
            chat_info = await self._telegram.get_chat_info(chat_id, bot_id)
            return chat_info.username if chat_info.username is not None else chat_info.title
        except:
            logger.error(f"Cannot get chat info for chat {chat_id}")
            return "Invalid chat identifier"

    async def _get_chat_and_bot_names(self, chat_id: str, bot_id: PydanticObjectId) -> tuple[str, str]:
        tasks = [
            asyncio.create_task(self._get_chat_name(chat_id, bot_id)),
            asyncio.create_task(self._get_bot_name(bot_id)),
        ]
        return await asyncio.gather(*tasks)


    async def get_chats(self) -> List[AllowedChatResponse]:
        chats = await self._chats.get_allowed_chats()

        async def process_chat(chat: AllowedChat) -> AllowedChatResponse:
            chat_name, bot_name = await self._get_chat_and_bot_names(chat.chat_id, chat.bot.id)
            return AllowedChatResponse(
                id           = chat.id,
                chat_id      = chat.chat_id,
                bot_id       = chat.bot.id,
                bot_name     = bot_name,
                chat_name    = chat_name,
                approve_date = chat.approve_date,
            )
        
        tasks = [
            asyncio.create_task(process_chat(chat))
            for chat in chats
        ]
        return await asyncio.gather(*tasks)

    async def get_chat_requests(self) -> List[ChatRequestResponse]:
        chats = await self._chats.get_chat_requests()

        async def process_chat(chat: ChatRequest) -> ChatRequestResponse:
            chat_name, bot_name = await self._get_chat_and_bot_names(chat.chat_id, chat.bot.id)
            return ChatRequestResponse(
                id           = chat.id,
                chat_id      = chat.chat_id,
                bot_id       = chat.bot.id,
                bot_name     = bot_name,
                chat_name    = chat_name,
                request_date = chat.request_date,
            )

        tasks = [
            asyncio.create_task(process_chat(chat))
            for chat in chats
        ]
        return await asyncio.gather(*tasks)

    async def approve_chat_request(self, request: ChatIdRequest):
        await self._chats.approve_chat_request(request.id)
        await self.broadcast_private("chats_updated")

    async def reject_chat_request(self, request: ChatIdRequest):
        await self._chats.reject_chat_request(request.id)
        await self.broadcast_private("chats_updated")

    async def disallow_chat(self, request: ChatIdRequest):
        await self._chats.disallow_chat(request.id)
        await self.broadcast_private("chats_updated")
