import hashlib
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Type

from pydantic import EmailStr

from ampf.base import KeyExistsException, KeyNotExistsException

from .auth_config import DefaultUser
from .auth_exceptions import (
    IncorectOldPasswordException,
    IncorrectUsernameOrPasswordException,
)
from .auth_model import AuthUser

_log = logging.getLogger(__name__)


class BaseUserService[T: AuthUser](ABC):
    """Base class for user service."""

    def __init__(self, user_class: Type[T] = AuthUser) -> None:
        self.user_class = user_class

    @abstractmethod
    async def is_empty(self) -> bool:
        """Checks if the storage is empty"""

    @abstractmethod
    async def get_user_by_email(self, email: EmailStr) -> T:
        """Gets user by email

        Args:
            email: Email of the user
        Returns:
            User object
        Raises:
            KeyNotExistsException: If user doesn't exist
        """

    @abstractmethod
    async def get(self, username: str) -> T:
        """Gets user by username

        Args:
            username: Username of the user
        Returns:
            User object
        Raises:
            KeyNotExistsException: If user doesn't exist
        """

    @abstractmethod
    async def put(self, username: str, user: T) -> None:
        """Puts user to storage

        Args:
            username: Username of the user
            user: User object
        """

    async def initialise_storage(self, default_user: DefaultUser) -> None:
        """Initialise storage with default user if it's empty

        Args:
            default_user: Default user configuration
        """
        if await self.is_empty():
            _log.warning("User storage is empty, creating default user")
            await self.create(self.user_class(**default_user.model_dump()))

    async def get_user_by_credentials(self, username: str, password: str) -> T:
        """Gets user by credentials and verifies password

        Args:
            username: Username of the user
            password: Password of the user
        Returns:
            User object
        Raises:
            IncorrectUsernameOrPasswordException: If username or password is incorrect
        """
        try:
            user = await self.get(username)
            if user.hashed_password != self._hash_password(password):
                _log.error("User %s password don't match", username)
                raise IncorrectUsernameOrPasswordException
            return user
        except KeyNotExistsException:
            _log.error("User %s not found", username)
            raise IncorrectUsernameOrPasswordException

    async def create(self, user: T) -> None:
        """Creates user

        Args:
            user: User object
        Raises:
            KeyExistsException: If user already exists
        """
        key = user.username
        try:
            await self.get(key)
            raise KeyExistsException
        except KeyNotExistsException:
            if user.password:
                user.hashed_password = self._hash_password(user.password)
                user.password = None
            await self.put(key, user)

    async def update(self, username: str, user: T) -> None:
        """Updates user

        Args:
            username: Username of the user
            user: User object
        Raises:
            KeyNotExistsException: If user doesn't exist
        """
        old = await self.get(username)
        if not old:
            raise KeyNotExistsException
        if user.password:
            user.hashed_password = self._hash_password(user.password)
            user.password = None
        else:
            user.hashed_password = old.hashed_password
        await self.put(username, user)

    def _hash_password(self, password: str) -> str:
        """Hashes password

        Args:
            password: Password to hash
        Returns:
            Hashed password
        """
        hashed_password = hashlib.sha256(password.encode("utf-8")).hexdigest()
        return hashed_password

    async def change_password(self, username: str, old_pass: str, new_pass: str) -> None:
        """Changes password for user

        Args:
            username: Username of the user
            old_pass: Old password
            new_pass: New password
        Raises:
            IncorectOldPasswordException: If old password is incorrect
            KeyNotExistsException: If user doesn't exist
        """
        try:
            user = await self.get_user_by_credentials(username, old_pass)
        except IncorrectUsernameOrPasswordException:
            raise IncorectOldPasswordException
        user.password = new_pass
        user.hashed_password = None
        await self.update(username, user)

    async def set_reset_code(self, username: str, reset_code: str, reset_code_exp: datetime) -> None:
        """Sets reset code for user

        Args:
            username: Username of the user
            reset_code: Reset code
            reset_code_exp: Expiration date of the reset code
        Raises:
            KeyNotExistsException: If user doesn't exist
        """
        user = await self.get(username)
        user.reset_code = reset_code
        user.reset_code_exp = reset_code_exp
        await self.update(username, user)
