from abc import ABC, abstractmethod

from shared.models.push_template import PushTemplate


class IPushTemplatesRepository(ABC):

    @abstractmethod
    async def get_all_templates(self) -> list[PushTemplate]:
        ...

    @abstractmethod
    async def get_template(self, topic: str) -> PushTemplate | None:
        ...

    @abstractmethod
    async def add_template(self, template: PushTemplate) -> PushTemplate:
        ...

    @abstractmethod
    async def save_template(self, template: PushTemplate) -> PushTemplate:
        ...
