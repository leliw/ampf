from abc import ABC, abstractmethod
from datetime import datetime
import hashlib
import logging

from pydantic import EmailStr

from ..base import KeyExistsException, KeyNotExistsException

from .auth_model import AuthUser
from .auth_exceptions import (
    IncorectOldPasswordException,
    IncorrectUsernameOrPasswordException,
)


class UserServiceBase[T: AuthUser](ABC):
    """Base class for user service."""

    def __init__(self):
        self._log = logging.getLogger(__name__)

    @abstractmethod
    def is_empty(self) -> bool:
        """True jeśl nie ma jeszcze żadnych użytkowników"""

    @abstractmethod
    def get_user_by_email(self, email: EmailStr) -> T:
        """Zwraca użytkownika po adresie email"""

    @abstractmethod
    def get(self, username: str) -> T:
        """Zwraca użytkownika po identyfikatorze"""

    @abstractmethod
    def put(self, username: str, user: T) -> None:
        """Zapisuje dane użytkownika"""

    def get_user_by_credentials(self, username: str, password: str) -> T:
        """Zwraca użytkownika po nazwie i haśle albo wyrzuca wyjątek"""
        try:
            user = self.get(username)
            if user.hashed_password != self._hash_password(password):
                self._log.error("User %s password don't match", username)
                raise IncorrectUsernameOrPasswordException
            return user
        except KeyNotExistsException:
            self._log.error("User %s not found", username)
            raise IncorrectUsernameOrPasswordException

    def create(self, user: T) -> None:
        key = user.username
        try:
            self.get(key)
            raise KeyExistsException
        except KeyNotExistsException:
            if user.password:
                user.hashed_password = self._hash_password(user.password)
                user.password = None
            self.put(key, user)

    def update(self, username: str, user: T) -> None:
        old = self.get(username)
        if not old:
            raise KeyNotExistsException
        if user.password:
            user.hashed_password = self._hash_password(user.password)
            user.password = None
        else:
            user.hashed_password = old.hashed_password
        self.put(username, user)

    def _hash_password(self, password: str):
        hashed_password = hashlib.sha256(password.encode("utf-8")).hexdigest()
        return hashed_password

    def change_password(self, username: str, old_pass: str, new_pass: str):
        try:
            user = self.get_user_by_credentials(username, old_pass)
        except IncorrectUsernameOrPasswordException:
            raise IncorectOldPasswordException
        user.password = new_pass
        user.hashed_password = None
        self.update(username, user)

    def set_reset_code(self, username: str, reset_code: str, reset_code_exp: datetime):
        user = self.get(username)
        user.reset_code = reset_code
        user.reset_code_exp = reset_code_exp
        self.update(username, user)
