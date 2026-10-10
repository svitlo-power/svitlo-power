import logging
from datetime import datetime
from beanie import PydanticObjectId

from shared.models.ext_data import ExtData
from shared.repositories.interfaces.ext_data_read import IExtDataReadRepository


logger = logging.getLogger(__name__)


class ExtDataReadRepository(IExtDataReadRepository):

    async def get_last_ext_data_by_user_id(self, user_id: PydanticObjectId) -> ExtData:
        documents = await ExtData.find(
            ExtData.user_id == user_id,
            fetch_links = True
        ).sort(
            -ExtData.received_at
        ).to_list()
        return documents[0] if documents else None

    async def get_ext_data_statistics(
        self,
        user_id: PydanticObjectId,
        start_date: datetime,
        end_date: datetime,
    ):
        ext_data = await ExtData.find(
            ExtData.user_id == user_id,
            ExtData.received_at >= start_date,
            ExtData.received_at <= end_date
        ).sort(
            ExtData.received_at
        ).to_list()

        return ext_data

    async def get_last_ext_data_before_date(self, user_id: int, before_date: datetime):
        try:
            docs = await ExtData.find(
                ExtData.user_id == user_id,
                ExtData.received_at < before_date
            ).sort(
                -ExtData.received_at
            ).limit(1).to_list()
            return docs[0] if docs else None
        except Exception as e:
            logger.error(f'Error getting last ext data before date: {e}')
            return None
