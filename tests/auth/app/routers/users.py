from fastapi import APIRouter, Depends

from ..features.user.user_model import User
from tests.auth.app.dependencies import Authorize, UserServceDep


router = APIRouter(
    tags=["Użytkownicy"], dependencies=[Depends(Authorize("admin"))]
)


@router.post("")
async def create(user_service: UserServceDep, user: User):
    user_service.create(user)
    return user


@router.get("")
async def get_all(user_service: UserServceDep):
    return user_service.get_all()


@router.get("/{username}")
async def get_by_email(user_service: UserServceDep, username: str) -> User:
    return user_service.get(username)


@router.put("/{username}")
async def update(user_service: UserServceDep, username: str, user: User):
    return user_service.update(username, user)


@router.delete("/{username}")
async def delete(user_service: UserServceDep, username: str):
    return user_service.delete(username)
