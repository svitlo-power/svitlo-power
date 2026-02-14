from datetime import datetime
from typing import Optional
from beanie import Document, iterative_migration

from shared.models.user import User as NewUser, ReportMode


class OldUser(Document):
    name: str
    password: Optional[str]
    is_active: bool = True
    is_reporter: bool = False
    api_key: Optional[str] = None
    password_reset_token: Optional[str] = None
    reset_token_expiration: Optional[datetime] = None

    class Settings:
        name = "users"

class Forward:
    @iterative_migration()
    async def set_report_mode(
        self,
        input_document: OldUser,
        output_document: NewUser,
    ):
        output_document.report_mode = ReportMode.EVENT

class Backward:
    @iterative_migration()
    async def reset_report_mode(
        self,
        input_document: OldUser,
        output_document: NewUser,
    ):
        pass
