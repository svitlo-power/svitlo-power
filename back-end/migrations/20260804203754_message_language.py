from datetime import datetime
from typing import Optional, List
from beanie import Document, Link, iterative_migration
from pydantic import Field

from shared.language import DEFAULT_LANGUAGE
from shared.models.bot import Bot
from shared.models.station import Station
from shared.models.message import Message as NewMessage


class OldMessage(Document):
    channel_id: Optional[str] = None
    name: Optional[str] = None
    message_template: Optional[str] = None
    should_send_template: Optional[str] = None
    timeout_template: Optional[str] = None

    bot: Optional[Link[Bot]] = None
    last_sent_time: Optional[datetime] = None
    enabled: Optional[bool] = True

    stations: List[Link[Station]] = Field(default_factory=list)

    class Settings:
        name = "messages"


class Forward:
    @iterative_migration()
    async def set_report_mode(
        self,
        input_document: OldMessage,
        output_document: NewMessage,
    ):
        output_document.language = DEFAULT_LANGUAGE

class Backward:
    @iterative_migration()
    async def reset_report_mode(
        self,
        input_document: OldMessage,
        output_document: NewMessage,
    ):
        pass
