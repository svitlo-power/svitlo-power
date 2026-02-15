from enum import Enum
from typing import List, Literal, Optional
from datetime import datetime
from beanie import Document
from pydantic import model_validator

from .beanie_filter import BeanieFilter
from .lookup import LookupModel, LookupValue


class ReportMode(str, Enum):
    PING = "ping"
    EVENT = "event"

class User(Document, LookupModel):
    name: str
    password: Optional[str]
    is_active: bool = True
    is_reporter: bool = False
    api_key: Optional[str] = None
    password_reset_token: Optional[str] = None
    reset_token_expiration: Optional[datetime] = None
    report_mode: Optional[ReportMode] = None

    class Settings:
        name = "users"

    @model_validator(mode="after")
    def validate_report_mode(self):
        if self.is_reporter:
            if self.report_mode is None:
                raise ValueError("report_mode must be set when is_reporter is True")
        else:
            self.report_mode = None
        return self

    def __str__(self):
        return (
            f"User(id={self.id}, name='{self.name}', "
            f"password='***', is_active={self.is_active}), "
            f"is_reporter={self.is_reporter}, report_mode={self.report_mode}"
        )

    @classmethod
    async def get_lookup_values(self, filter: BeanieFilter) -> List[LookupValue]:
        users = await self.find(filter).to_list()
        return [LookupValue(
            value = u.id,
            text  = u.name
        ) for u in users]

