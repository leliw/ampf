
from typing import List, override
from ampf.auth import UserServiceBase, DefaultUser
from ampf.base import BaseFactory
from tests.auth.app.features.user.user_model import UserHeader, User, UserInDB


class UserService(UserServiceBase):
    """Test implementation of UserServiceBase

    Adds storage and converts UserInDB to User and vice versa
    """

    def __init__(self, factory: BaseFactory):
        super().__init__()
        self.storage = factory.create_storage("users", UserInDB, key_name="email")

    @override
    def is_empty(self) -> bool:
        return self.storage.is_empty()

    @override
    def get_user_by_email(self, email: str) -> User:
        return self.get(email)

    @override
    def get(self, username: str) -> User:
        user_in_db = self.storage.get(username)
        return User(**dict(user_in_db))

    @override
    def put(self, username: str, user: User) -> None:
        user_in_db = UserInDB(**dict(user))
        self.storage.put(username, user_in_db)

    def get_all(self) -> List[UserHeader]:
        return [
            UserHeader(**i.model_dump(by_alias=True)) for i in self.storage.get_all()
        ]

    def delete(self, username: str) -> None:
        self.storage.delete(username)


def test_initialise_storage(factory: BaseFactory, test_user: DefaultUser):
    # Given: An empty UserService
    user_service = UserService(factory)
    assert user_service.is_empty()
    # When: The storage is initialised
    user_service.initialise_storage(test_user)
    # Then: The storage is not empty
    assert not user_service.is_empty()
    user = user_service.get(test_user.username)
    # And: Username is set
    assert user.username == test_user.username
    # And: Password (hashed) is set
    assert user.hashed_password
    # And: Roles are set
    assert user.roles == test_user.roles
