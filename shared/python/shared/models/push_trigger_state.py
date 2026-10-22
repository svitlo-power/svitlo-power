from datetime import datetime, timezone
from typing import Any
from beanie import Document
from pydantic import Field
from pymongo import ASCENDING, IndexModel


class PushTriggerState(Document):
    """State a push trigger keeps between checks, e.g. a building's confirmed power state."""
    key: str
    data: dict[str, Any] = Field(default_factory=dict)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "push_trigger_states"
        indexes = [
            IndexModel([("key", ASCENDING)], unique=True),
        ]
