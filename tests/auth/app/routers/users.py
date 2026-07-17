from fastapi import APIRouter, Depends

from ..features.user.user_model import User
from tests.auth.app.dependencies import Authorize, UserServiceDep


router = APIRouter(
    tags=["Użytkownicy"], dependencies=[Depends(Authorize("admin"))]
)


@router.post("")
async def create(user_service: UserServiceDep, user: User):
    await user_service.create(user)


@router.get("")
async def get_all(user_service: UserServiceDep):
    return await user_service.get_all()


@router.get("/{username}")
async def get_by_email(user_service: UserServiceDep, username: str) -> User:
    return await user_service.get(username)


@router.put("/{username}")
async def update(user_service: UserServiceDep, username: str, user: User):
    return await user_service.update(username, user)


@router.delete("/{username}")
async def delete(user_service: UserServiceDep, username: str):
    return await user_service.delete(username)
