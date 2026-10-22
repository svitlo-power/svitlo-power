from abc import ABC, abstractmethod
from typing import Any


class IPushTriggerStatesRepository(ABC):

    @abstractmethod
    async def get_state(self, key: str) -> dict[str, Any] | None:
        ...

    @abstractmethod
    async def set_state(self, key: str, data: dict[str, Any]):
        ...
