from abc import ABC, abstractmethod
from typing import List

from shared.models.user import User


class IUsersReadRepository(ABC):
    
    @abstractmethod
    async def get_user(self, user_name: str) -> User:
        ...

    @abstractmethod
    async def get_users(self, all: bool) -> List[User]:
        ...

    @abstractmethod
    async def get_user_by_id(self, user_id: str) -> User:
        ...

    @abstractmethod
    async def get_user_by_reset_token(self, token: str) -> User:
        ...
