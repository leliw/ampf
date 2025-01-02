from typing import List, Optional
from pydantic import EmailStr

from ampf.auth import UserServiceBase
from ampf.base import BaseFactory, KeyNotExistsException
from .user_model import User, UserInDB


class UserService(UserServiceBase[User]):
    """User service implementation"""

    def __init__(
        self,
        storage_factory: BaseFactory,
    ) -> None:
        super().__init__()
        self.storage = storage_factory.create_compact_storage(
            "users", UserInDB, "username"
        )

    def initialize_storege_with_user(self, default_user: User):
        if self.is_empty():
            self._log.warning("Initializing storage with default user")
            self.create(User(**default_user.model_dump()))

    def get_user_by_email(self, email: EmailStr) -> User:
        for user in self.storage.where("email", "==", email).get_all():
            return user
        raise KeyNotExistsException(email)

    def get_all(self) -> List[User]:
        return [User(**i.model_dump(by_alias=True)) for i in self.storage.get_all()]

    def get(self, key: str) -> Optional[User]:
        return self.storage.get(key)

    def put(self, key: str, user: User) -> None:
        user_in_db = UserInDB(**dict(user))
        self.storage.put(key, user_in_db)

    def delete(self, key: str) -> bool:
        return self.storage.delete(key)

    def is_empty(self) -> bool:
        return self.storage.is_empty()
