# Google OAuth

`GoogleOAuthService` provides a way to authenticate user with Google login.

## The authentication flow

1. Frontend calls backend `/api/google/login`
2. Backend redirects to Google with callback url `/api/google/callback`
3. Google calls callback with JWT containing user data
4. Backend creates exchange token and stores it with user data in cache
5. Backend redirects to frontend with exchange token in query params `/login?exchange-code=...`
6. Frontend calls backend with this token `/api/google/login?exchange-code=...`
7. Backend reads user data from storage, creates its own JWT and returns to frontend
8. Frontend uses received JWT to authorize all calls

### Backend

Required libraries:

```bash
uv add authlib itsdangerous
```

#### backend/app/app_config.py

Add required properties to configuration.

```python
    session_secret_key: str | None = None
    google_oauth_client_id: str | None = None
    google_oauth_client_secret: str | None = None 
```

#### backend/app/main.py

Authlib requires http session and Starlette Session requires secret key.

```python
from starlette.middleware.sessions import SessionMiddleware
...
app_config = AppConfig()  # pyright: ignore[reportCallIssue]
...
app.add_middleware(SessionMiddleware, secret_key=app_config.session_secret_key, session_cookie="session", max_age=1800)
```

#### backend/app/routers/auth_google.py

Define two endpoints: `/api/google/login` and `/api/google/callback`.

```python
from typing import Annotated

from ampf.auth import ExchangeCodePayload, GoogleOAuthConfig, GoogleOAuthService
from dependencies import AppConfigDep, AsyncFactoryDep, AuthServiceDep
from fastapi import APIRouter, Depends, Request, Query

router = APIRouter(tags=["Google authentication"])


def get_oauth(factory: AsyncFactoryDep, auth_service: AuthServiceDep, app_config: AppConfigDep) -> GoogleOAuthService:
    storage = factory.create_storage("google_oauth", ExchangeCodePayload, "exchange_code")
    return GoogleOAuthService(auth_service, storage, GoogleOAuthConfig(**app_config.model_dump()))


GoogleOAuthServiceDep = Annotated[GoogleOAuthService, Depends(get_oauth)]


@router.get("/login")
async def login(service: GoogleOAuthServiceDep, request: Request, base_url: str | None = None, code: Annotated[str | None, Query(alias="exchange-code")] = None):
    if code:
        return await service.authorize_with_code(code)
    else:
        return await service.authorize_redirect(request, base_url)


@router.get("/callback")
async def auth_callback(service: GoogleOAuthServiceDep, request: Request):
    return await service.auth_callback(request)
```

#### backend/app/routers/auth.py

Add router definition.

```python
...
from routers import auth_google
...
router.include_router(auth_google.router, prefix="/google")
```
