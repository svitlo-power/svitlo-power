from abc import ABC, abstractmethod

from shared.models.push_topic import PushTopic


class IPushTopicsRepository(ABC):
    @abstractmethod
    async def get_all_topics(self) -> list[PushTopic]:
        ...

    @abstractmethod
    async def get_enabled_topics(self) -> list[PushTopic]:
        ...

    @abstractmethod
    async def get_topic(self, key: str) -> PushTopic | None:
        ...

    @abstractmethod
    async def add_topic(self, topic: PushTopic) -> PushTopic:
        ...

    @abstractmethod
    async def set_enabled(self, key: str, enabled: bool) -> bool:
        ...
