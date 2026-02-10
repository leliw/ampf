import logging
from typing import List
from pydantic import EmailStr

from ampf.base import BaseAsyncFactory, KeyNotExistsException

from ampf.auth import BaseUserService
from .user_model import User, UserHeader, UserInDB

_log = logging.getLogger(__name__)


class UserService(BaseUserService[User]):
    """User service implementation"""

    def __init__(
        self,
        factory: BaseAsyncFactory,
    ) -> None:
        super().__init__(User)
        self.storage = factory.create_compact_storage("users", UserInDB, "username")

    async def get_user_by_email(self, email: EmailStr) -> User:
        async for user in self.storage.where("email", "==", email).get_all():
            return user
        raise KeyNotExistsException(email)

    async def get_all(self) -> List[UserHeader]:
        return [UserHeader(**i.model_dump(by_alias=True)) async for i in self.storage.get_all()]

    async def get(self, key: str) -> User:
        return await self.storage.get(key)

    async def put(self, key: str, user: User) -> None:
        user_in_db = UserInDB(**dict(user))
        await self.storage.put(key, user_in_db)

    async def delete(self, key: str) -> None:
        await self.storage.delete(key)

    async def is_empty(self) -> bool:
        return await self.storage.is_empty()
