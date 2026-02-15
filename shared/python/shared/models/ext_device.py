from datetime import datetime, timezone
from beanie import Document, Link, PydanticObjectId

from .user import User


class ExtDevice(Document):
    mac_address: str
    fw_version: str
    fs_version: str
    uptime: int
    updated_at: datetime = datetime.now(timezone.utc)
    user: Link[User] = None

    class Settings:
        name = "ext_device"
