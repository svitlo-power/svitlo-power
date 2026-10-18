from datetime import datetime, timezone
from beanie import Document
from pydantic import Field


class OutagesSchedule(Document):
    """Outages schedule document for MongoDB."""
    
    queue: str
    data: dict
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    class Settings:
        name = "outages_schedule"
        indexes = ["queue"]