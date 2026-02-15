from datetime import datetime, timezone
from beanie import PydanticObjectId
from injector import inject

from shared.models.ext_data import ExtData
from shared.models.user import User
from ..base import BaseService
from app.models.api import ExtDataItemResponse, ExtDataListRequest, ExtDataListResponse
from shared.services.events.service import EventsService
from app.repositories import DataQuery, IExtDataRepository, IUsersRepository


@inject
class ExtDataService(BaseService):
    def __init__(
        self,
        events: EventsService,
        ext_data: IExtDataRepository,
        users: IUsersRepository,
    ):
        super().__init__(events)
        self._ext_data = ext_data
        self._users = users


    def _process_ext_data(self, ext_data: ExtData):
        return ExtDataItemResponse(
            id          = ext_data.id,
            grid_state  = ext_data.grid_state,
            user_id     = ext_data.user_id,
            received_at = ext_data.received_at
        )


    async def _add_ext_data(self, user: User, grid_state: bool, date: datetime) -> PydanticObjectId:
        id = await self._ext_data.add_ext_data(user.id, grid_state, date)
        await self.broadcast_public("ext_data_updated")
        return id


    async def add_ext_data(self, user_name: str, grid_state: bool) -> PydanticObjectId:
        user = await self._users.get_user(user_name)

        if user is not None:
            date = datetime.now(timezone.utc)
            return await self._add_ext_data(user, grid_state, date)

        return None


    async def add_ext_data_by_user_id(self, user_id: PydanticObjectId, grid_state: bool, date: datetime = None):
        user = await self._users.get_user_by_id(user_id)

        if user is not None:
            date = date or datetime.now(timezone.utc)
            return await self._add_ext_data(user, grid_state, date)

        return None


    async def get_ext_data(self, request: ExtDataListRequest) -> ExtDataListResponse:
        query = DataQuery(
            filters = request.filters or [],
            sorting = request.sorting,
            paging  = request.paging,
        )
        ext_data, total = await self._ext_data.get_ext_data(query)

        return ExtDataListResponse(
            data=[self._process_ext_data(item) for item in ext_data],
            paging={
                "page": request.paging.page,
                "pageSize": request.paging.page_size,
                "total": total,
            }
        )


    async def get_by_id(self, ext_data_id: PydanticObjectId) -> ExtDataItemResponse:
        ext_data = await self._ext_data.get_ext_data_by_id(ext_data_id)

        if ext_data is None:
            return None

        return self._process_ext_data(ext_data)


    async def delete_ext_data(self, ext_data_id: PydanticObjectId):
        if await self._ext_data.delete(ext_data_id):
            await self.broadcast_public("ext_data_updated")
            return True
        return False
