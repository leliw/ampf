from typing import Annotated, List

from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm

from ampf.auth import (
    APIKey,
    APIKeyInDB,
    APIKeyRequest,
    ChangePasswordData,
    ResetPassword,
    ResetPasswordRequest,
    Tokens,
)
from tests.auth.app.dependencies import (
    AuthServiceDep,
    AuthTokenDep,
    TokenPayloadDep,
)

router = APIRouter(tags=["Autentykacja"])

UserFormDataDep = Annotated[OAuth2PasswordRequestForm, Depends()]


@router.post("/login")
async def login(auth_service: AuthServiceDep, form_data: UserFormDataDep) -> Tokens:
    return await auth_service.authorize(form_data.username, form_data.password)


@router.post("/logout")
async def logout(auth_service: AuthServiceDep, refresh_token: AuthTokenDep) -> None:
    await auth_service.add_to_black_list(refresh_token)


@router.post("/token-refresh")
async def refresh_token(auth_service: AuthServiceDep, refresh_token: AuthTokenDep) -> Tokens:
    return await auth_service.refresh_token(refresh_token)


@router.post("/change-password")
async def change_password(
    auth_service: AuthServiceDep,
    payload: ChangePasswordData,
    token_payload: TokenPayloadDep,
) -> None:
    await auth_service.change_password(token_payload.sub, payload.old_password, payload.new_password)


@router.post("/reset-password-request")
async def reset_password_request(auth_service: AuthServiceDep, rpr: ResetPasswordRequest):
    await auth_service.reset_password_request(rpr.email)


@router.post("/reset-password")
async def reset_password_route(auth_service: AuthServiceDep, rp: ResetPassword):
    await auth_service.reset_password(rp.email, rp.reset_code, rp.new_password)


@router.post("/api-keys")
async def generate_api_key(
    auth_service: AuthServiceDep, token_payload: TokenPayloadDep, request: APIKeyRequest
) -> APIKey:
    return await auth_service.generate_api_key(token_payload, request)


@router.get("/api-keys")
async def get_api_keys(auth_service: AuthServiceDep, token_payload: TokenPayloadDep) -> List[APIKeyInDB]:
    return [key async for key in auth_service.get_api_keys(token_payload)]


@router.delete("/api-keys/{key_hash}")
async def delete_api_key(auth_service: AuthServiceDep, token_payload: TokenPayloadDep, key_hash: str):
    return await auth_service.delete_api_key(token_payload, key_hash)
