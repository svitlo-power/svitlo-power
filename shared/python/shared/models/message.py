from datetime import datetime
from typing import Optional, List
from beanie import Document, Link
from pydantic import Field

from shared.models.beanie_filter import BeanieFilter

from .lookup import LookupModel, LookupValue
from .bot import Bot
from .station import Station


class Message(Document, LookupModel):
    channel_id: Optional[str] = None
    name: Optional[str] = None
    message_template: Optional[str] = None
    should_send_template: Optional[str] = None
    timeout_template: Optional[str] = None
    template_macros: Optional[str] = None

    bot: Optional[Link[Bot]] = None
    last_sent_time: Optional[datetime] = None
    enabled: Optional[bool] = True
    language: Optional[str] = None

    stations: List[Link[Station]] = Field(default_factory=list)

    class Settings:
        name = "messages"

    def __str__(self):
        station_ids = [str(s.id) for s in self.stations] if self.stations else []
        return (
            f"Message(id={self.id}, channel_id='{self.channel_id}', "
            f"name='{self.name}', stations={station_ids}, "
            f"last_sent_time={self.last_sent_time}, enabled={self.enabled}, "
            f"language={self.language})"
        )

    @classmethod
    async def get_lookup_values(self, filter: BeanieFilter) -> List[LookupValue]:
        messages = await self.find_all(filter).to_list()
        return [LookupValue(
            value = m.id,
            text  = m.name,
        ) for m in messages]
