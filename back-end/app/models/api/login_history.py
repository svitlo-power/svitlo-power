from datetime import datetime
from typing import List, Optional

from beanie import PydanticObjectId
from pydantic import BaseModel, Field

class LoginHistoryItemResponse(BaseModel):
    id: PydanticObjectId
    login_time: datetime = Field(alias="loginTime")
    ip_address: Optional[str] = Field(None, alias="ipAddress")

    model_config = {
        "populate_by_name": True,
        "from_attributes": True,
    }

__all__ = [
    "LoginHistoryItemResponse",
]
