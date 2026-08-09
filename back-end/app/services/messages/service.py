import asyncio
import logging
from contextlib import redirect_stdout
from datetime import datetime
import io
from typing import List
from beanie import PydanticObjectId
from injector import inject

from app.models.api import (
    MessageListResponseModel,
    MessageEditResponseModel,
    MessageCreateRequest,
    MessagePreviewRequest,
    MessagePreviewResponse,
    MessageUpdateRequest,
)
from app.repositories import IMessagesRepository, IStationsRepository
from shared.models.message import Message
from shared.services.events.service import EventsService
from ..telegram import TelegramService
from ..base import BaseService
from ..interfaces import IMessageGeneratorService


logger = logging.getLogger(__name__)


@inject
class MessagesService(BaseService):
    def __init__(
        self,
        events: EventsService,
        messages: IMessagesRepository,
        stations: IStationsRepository,
        message_generator: IMessageGeneratorService,
        telegram: TelegramService,
    ):
        super().__init__(events)
        self._messages = messages
        self._stations = stations
        self._telegram = telegram
        self._message_generator = message_generator


    async def _get_bot_name(self, bot_id: str):
        try:
            bot_info = await self._telegram.get_bot_info(bot_id)
            return bot_info.username
        except:
            logger.error(f'Cannot get bot info for bot {bot_id}')
            return 'Invalid bot identifier'


    async def _get_channel_name(self, channel_id: str, bot_id: str):
        try:
            chat_info = await self._telegram.get_chat_info(channel_id, bot_id)
            return chat_info.title
        except:
            logger.error(f'Cannot get channel info for channel {channel_id}')
            return 'Invalid channel identifier'


    async def _process_message(self, message):
        bot_name = await self._get_bot_name(message.bot.id)
        channel_name = await self._get_channel_name(message.channel_id, message.bot.id)
        stations = [station.id for station in message.stations]
        return MessageListResponseModel(
            id             = message.id,
            name           = message.name,
            channel_name   = channel_name,
            stations       = stations,
            bot_name       = bot_name,
            last_sent_time = message.last_sent_time,
            enabled        = message.enabled,
        )


    async def get_messages(self, all: bool = False) -> List[MessageListResponseModel]:
        messages = await self._messages.get_messages(all)

        tasks = [
            asyncio.create_task(self._process_message(message))
            for message in messages
        ]

        return await asyncio.gather(*tasks)


    async def get_message(self, message_id: PydanticObjectId) -> MessageEditResponseModel:
        message = await self._messages.get_message(message_id)

        bot_name = await self._get_bot_name(message.bot.id)
        channel_name = await self._get_channel_name(message.channel_id, message.bot.id)
        stations = [station.id for station in message.stations]
        return MessageEditResponseModel(
            id                   = message.id,
            name                 = message.name,
            bot_id               = message.bot.id,
            template_macros      = message.template_macros,
            should_send_template = message.should_send_template,
            timeout_template     = message.timeout_template,
            message_template     = message.message_template,
            enabled              = message.enabled,
            stations             = stations,
            last_sent_time       = message.last_sent_time,
            bot_name             = bot_name,
            channel_name         = channel_name,
            channel_id           = message.channel_id,
            language             = message.language
        )


    async def save_state(self, message_id: PydanticObjectId, state: bool):
        await self._messages.save_state(message_id, state)
        self.broadcast_private("messages_updated")


    async def create_message(self, dto: MessageCreateRequest):
        message = await self._messages.create(dto.model_dump())
        self.broadcast_private("messages_updated")
        return message.id


    async def update_message(self, id: PydanticObjectId, dto: MessageUpdateRequest):
        message = await self._messages.update(id, dto.model_dump())
        self.broadcast_private("messages_updated")
        return message.id
    
    async def get_message_preview(self, message_preview: MessagePreviewRequest) -> MessagePreviewResponse:
        server_stations = await self._stations.get_stations(True)
        id_set = set(message_preview.stations)
        stations = [s for s in server_stations if s.id in id_set]
        
        last_sent_time: datetime = None

        if message_preview.id is not None:
            existing_message = await self._messages.get_message(message_preview.id)
            if existing_message is not None:
                last_sent_time = existing_message.last_sent_time

        message = Message(
            name                 = message_preview.name,
            message_template     = message_preview.message_template,
            timeout_template     = message_preview.timeout_template,
            should_send_template = message_preview.should_send_template,
            template_macros      = message_preview.template_macros,
            stations             = stations,
            last_sent_time       = last_sent_time,
            language             = message_preview.language,
        )

        stdout_buffer = io.StringIO()

        try:
            info = None
            with redirect_stdout(stdout_buffer):
                info = await self._message_generator.generate_message(message, True)

            if info is None:
                captured_output = stdout_buffer.getvalue()
                raise Exception(captured_output)

            return MessagePreviewResponse(
                success        = True,
                message        = info.message,
                should_send    = info.should_send,
                timeout        = info.timeout,
                next_send_time = info.next_send_time
            )
        except Exception as e:
            raise e
