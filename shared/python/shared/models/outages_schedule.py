from datetime import datetime
from typing import Optional
from beanie import Document
from pydantic import Field


class OutagesSchedule(Document):
    """Outages schedule document for MongoDB."""
    
    queue: str
    data: dict
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    class Settings:
        name = "outages_schedule"
        indexes = ["queue"]