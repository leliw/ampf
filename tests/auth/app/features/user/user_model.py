from typing import Any, Dict

from pydantic import model_serializer

from ampf.auth.auth_model import AuthUser


class UserHeader(AuthUser):
    pass


class User(UserHeader):
    pass


class UserInDB(User):
    @model_serializer
    def ser_model(self) -> Dict[str, Any]:
        self.password = None
        return dict(self)
