from datetime import datetime, timezone
from enum import Enum
from beanie import Document, PydanticObjectId
from pydantic import Field
from pymongo import ASCENDING, IndexModel


class PushPlatform(str, Enum):
    Android = "android"
    Web = "web"


class PushDevice(Document):
    token: str
    platform: PushPlatform
    language: str = "uk"
    enabled: bool = True
    # Opt-out: the device gets every enabled topic except these, so new topics reach everyone.
    disabled_topics: list[str] = Field(default_factory=list)
    # Empty means all buildings.
    buildings: list[PydanticObjectId] = Field(default_factory=list)
    app_version: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_seen: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    class Settings:
        name = "push_devices"
        indexes = [
            IndexModel([("token", ASCENDING)], unique=True),
        ]
