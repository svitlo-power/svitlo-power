from abc import ABC, abstractmethod
from typing import Callable

from .models import EventItem


class EventsTransport(ABC):

    @abstractmethod
    async def publish(self, channel: str, event: EventItem):
        pass

    @abstractmethod
    async def start_subscriber(self, handler: Callable[[str, EventItem], None]):
        pass


class LocalTransport(EventsTransport):
    def __init__(self):
        self.handler = None

    async def publish(self, channel, event):
        if self.handler:
            await self.handler(channel, event)

    async def start_subscriber(self, handler):
        self.handler = handler
