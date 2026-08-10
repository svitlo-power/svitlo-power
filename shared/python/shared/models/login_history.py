from datetime import datetime, timezone
from typing import Optional

from beanie import Document
from beanie.odm.fields import PydanticObjectId

from .user import User


class LoginHistory(Document):
    user_id: PydanticObjectId
    login_time: datetime = datetime.now(timezone.utc)
    ip_address: Optional[str] = None

    class Settings:
        name = "login_history"

    @property
    async def user(self) -> User:
        return await User.get(self.user_id)

    def to_dict(self):
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "login_time": self.login_time.isoformat() if self.login_time else None,
            "ip_address": self.ip_address,
        }
