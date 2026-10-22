from beanie.operators import In
from pymongo.errors import DuplicateKeyError

from shared.models.push_delivery import PushDelivery
from ..interfaces.push_deliveries import IPushDeliveriesRepository


class PushDeliveriesRepository(IPushDeliveriesRepository):

    async def try_insert(self, delivery: PushDelivery) -> bool:
        # The unique dedup_key index makes the insert atomic across retries and instances
        try:
            await delivery.insert()
        except DuplicateKeyError:
            return False
        return True

    async def save(self, delivery: PushDelivery) -> PushDelivery:
        await delivery.save()
        return delivery

    async def get_recent(self, limit: int) -> list[PushDelivery]:
        return await PushDelivery.find_all().sort(-PushDelivery.created_at).limit(limit).to_list()

    async def get_by_keys(self, dedup_keys: list[str]) -> list[PushDelivery]:
        if not dedup_keys:
            return []
        return await PushDelivery.find(In(PushDelivery.dedup_key, dedup_keys)).to_list()
