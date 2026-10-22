from abc import ABC, abstractmethod

from shared.models.push_delivery import PushDelivery


class IPushDeliveriesRepository(ABC):

    @abstractmethod
    async def try_insert(self, delivery: PushDelivery) -> bool:
        """Inserts the record; returns False when a record with the same dedup_key already exists."""
        ...

    @abstractmethod
    async def save(self, delivery: PushDelivery) -> PushDelivery:
        ...

    @abstractmethod
    async def get_recent(self, limit: int) -> list[PushDelivery]:
        ...

    @abstractmethod
    async def get_by_keys(self, dedup_keys: list[str]) -> list[PushDelivery]:
        ...
