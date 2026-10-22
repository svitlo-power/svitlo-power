from datetime import datetime, timezone
from beanie import Document
from pydantic import Field
from pymongo import ASCENDING, IndexModel

from .localizable_value import LocalizableValue


class PushTemplate(Document):
    """Admin-editable Jinja2 template of the notification sent for a topic's event."""
    topic: str
    enabled: bool = True
    # Jinja2 templates per language; a missing language falls back to the default one
    title: LocalizableValue
    body: LocalizableValue
    # Jinja2 template of the app path opened on tap
    route: str = ""
    # Optional Jinja2 condition; the notification is sent only when it renders to True
    should_send: str | None = None
    macros: str | None = None
    # Trigger parameters, e.g. lead_minutes or debounce_seconds
    params: dict[str, int] = Field(default_factory=dict)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "push_templates"
        indexes = [
            IndexModel([("topic", ASCENDING)], unique=True),
        ]
