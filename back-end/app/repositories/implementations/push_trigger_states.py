from datetime import datetime, timezone
from typing import Any

from beanie.operators import Set

from shared.models.push_trigger_state import PushTriggerState
from ..interfaces.push_trigger_states import IPushTriggerStatesRepository


class PushTriggerStatesRepository(IPushTriggerStatesRepository):

    async def get_state(self, key: str) -> dict[str, Any] | None:
        state = await PushTriggerState.find_one(PushTriggerState.key == key)
        return state.data if state else None

    async def set_state(self, key: str, data: dict[str, Any]):
        await PushTriggerState.find_one(PushTriggerState.key == key).upsert(
            Set({ PushTriggerState.data: data, PushTriggerState.updated_at: datetime.now(timezone.utc) }),
            on_insert=PushTriggerState(key=key, data=data),
        )
