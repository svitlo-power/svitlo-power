from datetime import datetime
from typing import List

from beanie import PydanticObjectId
from shared.models.user import User, ReportMode
from ..interfaces.users import IUsersRepository


class UsersRepository(IUsersRepository):
    async def get_user(self, user_name: str):
        return await User.find_one(User.is_active == True, User.name == user_name)

    async def get_users(self, all: bool) -> List[User]:
        query = {} if all else {"is_active": True}
        return await User.find(query).to_list()

    async def get_user_by_id(self, user_id: str) -> User:
        return await User.find_one(User.id == PydanticObjectId(user_id), User.is_active == True)

    async def get_user_by_reset_token(self, token: str):
        return await User.find_one(User.password_reset_token == token, User.is_active == True)

    async def rename_user(self, user_id: str, user_name: str):
        existing_user: User = await self.get_user_by_id(user_id)
        if existing_user:
            existing_user.name = user_name
            await existing_user.save()

    async def set_password_reset_token(
        self,
        user_id: str,
        reset_token: str,
        reset_token_expiration: datetime,
    ):
        existing_user: User = await self.get_user_by_id(user_id)
        if existing_user:
            existing_user.password_reset_token = reset_token
            existing_user.reset_token_expiration = reset_token_expiration
            await existing_user.save()
        else:
            raise ValueError("Cannot find user")

    def _remove_password_reset_token(self, user: User):
        user.password_reset_token = None
        user.reset_token_expiration = None

    async def remove_password_reset_token(
        self,
        user_id: str,
    ):
        existing_user: User = await self.get_user_by_id(user_id)
        if existing_user:
            self._remove_password_reset_token(existing_user)
            existing_user.save()

    async def change_password(self, user_id: str, new_password: str):
        existing_user: User = await self.get_user_by_id(user_id)
        if existing_user:
            existing_user.password = new_password
            self._remove_password_reset_token(existing_user)
            await existing_user.save()

    async def create_user(
        self,
        user_name: str,
        is_active: bool,
        is_reporter: bool,
        password_reset_token: str,
        reset_token_expiration: str,
        report_mode: ReportMode,
    ) -> PydanticObjectId:
        existing_user = await self.get_user(user_name)
        if not existing_user:
            user = User(
                name                   = user_name,
                password               = None,
                is_active              = is_active,
                is_reporter            = is_reporter,
                password_reset_token   = password_reset_token,
                reset_token_expiration = reset_token_expiration,
                report_mode            = report_mode,
            )
            await user.insert()
            return user.id
        return None

    async def force_create_user(
        self,
        user_name: str,
        password: str,
    ) -> PydanticObjectId:
        existing_user = await self.get_user(user_name)
        if not existing_user:
            user = User(
                name        = user_name,
                is_active   = True,
                is_reporter = False,
                password    = password,
            )
            await user.insert()
            return user.id
        return None

    async def update_user(
        self,
        id: str,
        user_name: str,
        is_active: bool,
        is_reporter: bool,
        report_mode: ReportMode,
    ) -> str:
        existing_user = await self.get_user_by_id(id)
        if not existing_user:
            return

        if not is_reporter and getattr(existing_user, "api_key", None):
            existing_user.api_key = None

        if existing_user.is_reporter and not is_reporter:
            existing_user.password_reset_token = None
            existing_user.reset_token_expiration = None

        existing_user.name = user_name
        existing_user.is_active = is_active
        existing_user.is_reporter = is_reporter
        existing_user.report_mode = report_mode
        await existing_user.save()

    async def delete_user(self, user_id: str) -> bool:
        existing_user: User = await self.get_user_by_id(user_id)
        if existing_user:
            await existing_user.delete()
            return True

        return False

    async def save_user_api_key(self, user_id: str, api_key: str) -> bool:
        existing_user: User = await self.get_user_by_id(user_id)
        if existing_user:
            existing_user.api_key = api_key
            await existing_user.save()
            return True

        return False
