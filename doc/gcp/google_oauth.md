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
    session_secret_key: str
    google_oauth_client_id: str | None = None
    google_oauth_client_secret: str | None = None 
```

#### backend/app/main.py

Authlib requires http session and Starlette Session requires secret key.
Name `__session` is **required** by Firebase.

```python
...
app_config = AppConfig()  # pyright: ignore[reportCallIssue]
...
if app_config.session_secret_key:
    from starlette.middleware.sessions import SessionMiddleware

    app.add_middleware(SessionMiddleware, secret_key=app_config.session_secret_key, session_cookie="__session", max_age=1800)
...
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

### Frontend

#### src/app/core/auth/auth.interceptor.ts

Exclude `/api/google/login` route.

```typescript
const EXCLUDED_ROUTES = [
    ...
    '/api/google/login',
    ...
];
```

#### src/app/core/auth/auth.service.ts

Add login with exchange code.

```typescript
    ...
    loginWithExchangeCode(code: string, store_token = false): Observable<Tokens> {
        this.store_token = store_token;
        return this.http.get<Tokens>('/api/google/login', { params: { "exchange-code": code } }).pipe(
            tap((value) => this.setData(value))
        );
    }
    ...
````

#### src/app/core/auth/login-form/login-form.component.html

Add Google Sign in button.

```html
                ...
                <div class="divider">
                    <span>or</span>
                </div>

                <button mat-stroked-button type="button" class="google-btn full-width" (click)="loginWithGoogle()">
                    <img src="google-icon.svg" alt="Google icon" class="google-icon">
                    Sign in with Google
                </button>
                ...
```

#### public/google-icon.svg

```svg
<svg xmlns="http://www.w3.org/2000/svg" height="24" viewBox="0 0 24 24" width="24">
    <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/>
    <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
    <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
    <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
    <path d="M1 1h22v22H1z" fill="none"/>
</svg>
```

#### src/app/core/auth/login-form/login-form.component.ts

```typescript
export class LoginFormComponent implements OnInit, OnDestroy {
    ...
    private loader = inject(FullscreenLoaderService)

    constructor() {
        if (this.authService.isAuthenticated())
            this.router.navigate(['/']);
        this.store_token = JSON.parse(sessionStorage.getItem('remember_me') ?? 'false');
    }

    ngOnInit(): void {
        this.version$ = this.configService.getConfigValue$("version");
        this.activatedRoute.queryParams.pipe(
            map(params => params['exchange-code']),
            filter(code => !!code),
            take(1),
            switchMap(code => {
                this.loader.show({ message: 'Signing in ...' });
                const rememberMe = JSON.parse(sessionStorage.getItem('remember_me') || 'false');
                return this.authService.loginWithExchangeCode(code, rememberMe);
            })
        ).subscribe({
            error: (err) => {
                this.loader.hide();
                if (err.status === 401)
                    this.snackBar.open('Authentication failed', 'Close', { duration: 1500 });
                else {
                    console.warn(err.message);
                    this.snackBar.open(err.message, 'Close');
                }
            }
        });
    }

    ngOnDestroy(): void {
        if (this.loader.isVisible())
            this.loader.hide();
    }
...
    loginWithGoogle() {
        sessionStorage.setItem('remember_me', JSON.stringify(this.store_token));
        const baseUrl = window.location.origin;
        window.location.href = `/api/google/login?base_url=` + encodeURIComponent(baseUrl);
    }
```
