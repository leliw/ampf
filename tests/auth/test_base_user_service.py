from typing import List

import pytest
from pydantic import EmailStr

from ampf.auth import BaseUserService, DefaultUser
from ampf.base.base_async_factory import BaseAsyncFactory
from ampf.base.exceptions import KeyNotExistsException
from tests.auth.app.features.user.user_model import User, UserHeader, UserInDB


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


@pytest.mark.asyncio
async def test_create_existing_user(factory: BaseAsyncFactory):
    # Given: An user initialised service
    user_service = UserService(factory)
    await user_service.create(User(username="admin@gmail.com", password="admin"))
    # When: I create an existing user
    with pytest.raises(Exception):
        await user_service.create(User(username="admin@gmail.com", password="admin"))


@pytest.mark.asyncio
async def test_get_user_by_email(factory: BaseAsyncFactory):
    # Given: An user initialised service
    user_service = UserService(factory)
    await user_service.initialise_storage(DefaultUser(username="admin@gmail.com", password="admin"))
    # When: I get user by email
    user = await user_service.get_user_by_email("admin@gmail.com")
    # Then: The user is returned
    assert user.username == "admin@gmail.com"


@pytest.mark.asyncio
async def test_get_user_by_credentials_ok(factory: BaseAsyncFactory):
    # Given: An user initialised service
    user_service = UserService(factory)
    await user_service.initialise_storage(DefaultUser(username="admin@gmail.com", password="admin"))
    # When: I get user by credentials
    user = await user_service.get_user_by_credentials("admin@gmail.com", "admin")
    # Then: The user is returned
    assert user.username == "admin@gmail.com"


@pytest.mark.asyncio
async def test_get_user_by_credentials_wrong_user(factory: BaseAsyncFactory):
    # Given: An user initialised service
    user_service = UserService(factory)
    await user_service.initialise_storage(DefaultUser(username="admin@gmail.com", password="admin"))
    # When: I get user by credentials with wrong user
    with pytest.raises(Exception):
        await user_service.get_user_by_credentials("admin1@gmail.com", "admin")


@pytest.mark.asyncio
async def test_get_user_by_credentials_wrong_password(factory: BaseAsyncFactory):
    # Given: An user initialised service
    user_service = UserService(factory)
    await user_service.initialise_storage(DefaultUser(username="admin@gmail.com", password="admin"))
    # When: I get user by credentials with wrong password
    with pytest.raises(Exception):
        await user_service.get_user_by_credentials("admin@gmail.com", "admin1")
