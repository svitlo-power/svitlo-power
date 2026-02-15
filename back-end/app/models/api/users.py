from typing import Optional
from beanie import PydanticObjectId
from pydantic import BaseModel, Field

from shared.models.user import ReportMode


class UserListResponseModel(BaseModel):
    id: PydanticObjectId
    name: str
    is_active: bool = Field(True, alias='isActive')
    is_reporter: bool = Field(False, alias='isReporter')
    api_key: Optional[str] = Field(None, alias='apiKey')
    report_mode: Optional[ReportMode] = Field(None, alias='reportMode')

    model_config = {
        "populate_by_name": True,
        "from_attributes": True,
    }

__all__ = [
    "UserListResponseModel",
]
