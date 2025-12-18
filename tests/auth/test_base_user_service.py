
import logging
from typing import List

from pydantic import EmailStr
import pytest
from ampf.auth import BaseUserService, DefaultUser
from ampf.base.base_async_factory import BaseAsyncFactory
from ampf.base.exceptions import KeyNotExistsException
from tests.auth.app.features.user.user_model import UserHeader, User, UserInDB


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
    

@pytest.mark.asyncio
async def test_initialise_storage(factory: BaseAsyncFactory, test_user: DefaultUser):
    # Given: An empty UserService
    user_service = UserService(factory)
    assert user_service.is_empty()
    # When: The storage is initialised
    await user_service.initialise_storage(test_user)
    # Then: The storage is not empty
    assert not await user_service.is_empty()
    user = await user_service.get(test_user.username)
    # And: Username is set
    assert user.username == test_user.username
    # And: Password (hashed) is set
    assert user.hashed_password
    # And: Roles are set
    assert user.roles == test_user.roles
