from datetime import datetime, timezone
from beanie import Document
from pydantic import Field

from .localizable_value import LocalizableValue


class Announcement(Document):
    title: LocalizableValue
    body: LocalizableValue
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "announcements"
