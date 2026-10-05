import logging
from datetime import datetime, timedelta, timezone
from typing import List
from beanie import PydanticObjectId
from pymongo import ASCENDING, DESCENDING
from shared.repositories import ExtDataReadRepository

from .base import BaseReadRepository
from shared.models.ext_data import ExtData
from app.models.sorting_config import SortingConfig
from ..interfaces import DataQuery
from ..interfaces.ext_data import IExtDataRepository


logger = logging.getLogger(__name__)


class ExtDataRepository(ExtDataReadRepository, IExtDataRepository, BaseReadRepository[ExtData]):
    model = ExtData

    def build_reference_joins(self, sorting: SortingConfig | None) -> list[dict]:
        if sorting and sorting.column == "user_id":
            return [
                {
                    "$lookup": {
                        "from": "users",
                        "localField": "user_id",
                        "foreignField": "_id",
                        "as": "user",
                    }
                },
                {"$unwind": "$user"},
            ]
        return []

    def build_sort_stage(self, sorting: SortingConfig | None) -> dict:
        if not sorting:
            return {}

        if sorting.column == "user_id":
            sort_field = "user.name"
        else:
            return super().build_sort_stage(sorting)

        direction = ASCENDING if sorting.order == "asc" else DESCENDING
        return {sort_field: direction}


    async def get_ext_data(self, query: DataQuery = None) -> tuple[List[ExtData], int]:
        return await self.get_data(query)

    async def get_ext_data_by_id(self, ext_data_id: PydanticObjectId) -> ExtData:
        return await ExtData.get(ext_data_id)

    async def add_ext_data(
        self,
        user_id: PydanticObjectId,
        grid_state: bool,
        date: datetime,
    ) -> PydanticObjectId:
        ext_data = ExtData(
            user_id     = user_id,
            grid_state  = grid_state,
            received_at = date,
        )
        await ext_data.insert()
        return ext_data.id

    async def delete(self, ext_data_id: PydanticObjectId) -> bool:
        ext_data = await ExtData.get(ext_data_id)
        if ext_data:
            await ext_data.delete()
            return True
        return False

    async def delete_old_data(self, keep_days: int):
        timeout = datetime.now(timezone.utc) - timedelta(days = keep_days)
        logger.info(f"removing ext data older than {timeout}")

        await ExtData.find(
            ExtData.received_at < timeout
        ).delete()
