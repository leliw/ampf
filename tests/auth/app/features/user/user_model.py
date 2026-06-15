from typing import Any

from pydantic import model_serializer

from ampf.auth.auth_model import AuthUser


class UserHeader(AuthUser):
    pass


class User(UserHeader):
    pass


class UserInDB(User):
    @model_serializer
    def ser_model(self) -> dict[str, Any]:
        ret = dict(self)
        ret.pop("password", None)
        return ret
