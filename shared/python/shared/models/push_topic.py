from beanie import Document
from pymongo import ASCENDING, IndexModel

from .localizable_value import LocalizableValue


class PushTopic(Document):
    key: str
    name: LocalizableValue
    description: LocalizableValue
    enabled: bool = True
    order: int = 0

    class Settings:
        name = "push_topics"
        indexes = [
            IndexModel([("key", ASCENDING)], unique=True),
        ]
