from datetime import datetime, timezone
from enum import Enum
from beanie import Document, PydanticObjectId
from pydantic import Field
from pymongo import ASCENDING, DESCENDING, IndexModel


# Delivery records are kept for 30 days; the TTL index removes older ones
DELIVERY_TTL_SECONDS = 30 * 24 * 60 * 60


class PushDeliveryStatus(str, Enum):
    Pending = "pending"
    Sent = "sent"
    Failed = "failed"
    SkippedTopicDisabled = "skipped_topic_disabled"
    SkippedTemplateDisabled = "skipped_template_disabled"
    SkippedCondition = "skipped_condition"
    NoRecipients = "no_recipients"


class PushDelivery(Document):
    # One record per event; the unique index makes repeated events a no-op
    dedup_key: str
    topic: str
    # Short description of the event for the admin log, never device tokens
    summary: dict[str, str] = Field(default_factory=dict)
    building_id: PydanticObjectId | None = None
    status: PushDeliveryStatus = PushDeliveryStatus.Pending
    recipients: int = 0
    recipients_by_language: dict[str, int] = Field(default_factory=dict)
    success_count: int = 0
    failure_count: int = 0
    invalid_removed: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    error: str | None = None

    class Settings:
        name = "push_deliveries"
        indexes = [
            IndexModel([("dedup_key", ASCENDING)], unique=True),
            IndexModel([("created_at", DESCENDING)], expireAfterSeconds=DELIVERY_TTL_SECONDS),
        ]
