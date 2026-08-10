import logging
from datetime import datetime, timezone
from typing import List, Tuple

from beanie import PydanticObjectId
from pymongo import DESCENDING

from .base import BaseReadRepository
from shared.models.login_history import LoginHistory
from app.models.sorting_config import SortingConfig
from ..interfaces import DataQuery
from ..interfaces.login_history import ILoginHistoryRepository


logger = logging.getLogger(__name__)


class LoginHistoryRepository(ILoginHistoryRepository, BaseReadRepository[LoginHistory]):
    model = LoginHistory

    async def get_login_history(
        self,
        user_id: PydanticObjectId
    ) -> List[LoginHistory]:

        query = {
            "user_id": user_id
        }
        return (
            await LoginHistory.find(query, fetch_links=True)
            .sort(-LoginHistory.login_time)
            .to_list()
        )


    async def add_login_history(
        self,
        user_id: PydanticObjectId,
        ip_address: str = None,
    ) -> PydanticObjectId:
        history = LoginHistory(
            user_id=user_id,
            login_time=datetime.now(timezone.utc),
            ip_address=ip_address,
        )
        await history.insert()
        return history.id
