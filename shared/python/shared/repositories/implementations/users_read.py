from abc import ABC, abstractmethod
from typing import List

from beanie import PydanticObjectId

from shared.models.user import User
from shared.repositories.interfaces.users_read import IUsersReadRepository


class UsersReadRepository(IUsersReadRepository):
    
    async def get_user(self, user_name: str):
        return await User.find_one(User.is_active == True, User.name == user_name)

    async def get_users(self, all: bool) -> List[User]:
        query = {} if all else {"is_active": True}
        return await User.find(query).to_list()

    async def get_user_by_id(self, user_id: str) -> User:
        return await User.find_one(User.id == PydanticObjectId(user_id), User.is_active == True)

    async def get_user_by_reset_token(self, token: str):
        return await User.find_one(User.password_reset_token == token, User.is_active == True)
