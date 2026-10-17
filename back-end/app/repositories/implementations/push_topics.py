from beanie.operators import Set
from shared.models.push_topic import PushTopic
from ..interfaces.push_topics import IPushTopicsRepository


class PushTopicsRepository(IPushTopicsRepository):

    async def get_all_topics(self) -> list[PushTopic]:
        return await PushTopic.find_all().sort(+PushTopic.order).to_list()

    async def get_enabled_topics(self) -> list[PushTopic]:
        return await PushTopic.find(PushTopic.enabled == True).sort(+PushTopic.order).to_list()

    async def get_topic(self, key: str) -> PushTopic | None:
        return await PushTopic.find_one(PushTopic.key == key)

    async def add_topic(self, topic: PushTopic) -> PushTopic:
        await topic.insert()
        return topic

    async def set_enabled(self, key: str, enabled: bool) -> bool:
        result = await PushTopic.find_one(PushTopic.key == key).update(Set({PushTopic.enabled: enabled}))
        return bool(result and result.matched_count)
