# Authentication & Authorization

1. Backend - local authentication
    1. User management (CRUD)
    2. Authentication & authorization
    3. Password reset functionality
2. Frontend - authentication
    1. User authentication service & interceptor
    2. User login form
    3. User management (CRUD) & authorization
    4. Change password & logout
    5. Password reset

## 1.1 Backend - User management (CRUD)

### User model

Simplest classes.

```python
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
```

### User service

```python
from pydantic import EmailStr

from ampf.base import BaseAsyncFactory, KeyNotExistsException

from ampf.auth import BaseUserService
from .user_model import User, UserHeader, UserInDB


class UserService(BaseUserService[User]):
    """User service implementation"""

    def __init__(self, factory: BaseAsyncFactory) -> None:
        super().__init__(User)
        self.storage = factory.create_compact_storage("users", UserInDB, "username")

    async def get_user_by_email(self, email: EmailStr) -> User:
        async for user in self.storage.where("email", "==", email).get_all():
            return user
        raise KeyNotExistsException(email)

    async def get_all(self) -> list[UserHeader]:
        return [UserHeader(**i.model_dump(by_alias=True)) async for i in self.storage.get_all()]

    async def get(self, key: str) -> User:
        return await self.storage.get(key)

    async def put(self, key: str, user: User) -> None:
        user_in_db = UserInDB(**dict(user))
        await self.storage.put(key, user_in_db)

    async def delete(self, key: str) -> None:
        await self.storage.delete(key)

    async def is_empty(self) -> bool:
        return await self.storage.is_empty()
```

### Users router

```python
from fastapi import APIRouter

from core.users.user_model import User
from dependencies import UserServiceDep


router = APIRouter(tags=["Użytkownicy"])


@router.post("")
async def create(user_service: UserServiceDep, user: User):
    await user_service.create(user)


@router.get("")
async def get_all(user_service: UserServiceDep):
    return await user_service.get_all()


@router.get("/{username}")
async def get(user_service: UserServiceDep, username: str) -> User:
    return await user_service.get(username)


@router.put("/{username}")
async def update(user_service: UserServiceDep, username: str, user: User):
    return await user_service.update(username, user)


@router.delete("/{username}")
async def delete(user_service: UserServiceDep, username: str):
    return await user_service.delete(username)
```

Also add in `main.py`.

```python
app.include_router(users.router, prefix="/api/users")
```

### Config - DefaultUser

Add `default_user` property to `AppConfig`.

```python
    default_user: DefaultUser = DefaultUser(username="admin", password="")
```

### Dependency - UserServiceDep

```python
async def user_service_dep(app_config: AppConfigDep, factory: AsyncFactoryDep) -> UserService:
    service = UserService(factory)
    await service.initialise_storage(app_config.default_user)
    return service


UserServiceDep = Annotated[UserService, Depends(user_service_dep)]
```

### Tests - Users

The headers fixture will be changed later.

```python
import pytest

from core.users.user_model import User, UserHeader
from ampf.testing import ApiTestClient

@pytest.fixture
def headers() -> dict[str, str]:
    return {}


def test_get_all(client: ApiTestClient, headers):
    # Given: An initialized storage with default user
    # When: I get all users
    r = client.get_typed_list("/api/users", 200, UserHeader, headers=headers)
    # Then: I get only default user
    assert 1 == len(r)


def test_post_get_put_delete(client: ApiTestClient, headers):
    # POST
    user = User(username="mr.bean@gmail.com", email="mr.bean@gmail.com")
    client.post("/api/users", 200, json=user, headers=headers)

    # GET
    r = client.get_typed(f"/api/users/{user.username}", 200, User, headers=headers)
    assert user.username == r.username

    # PUT
    user.email = "mr.bean2@gmail.com"
    r = client.put(f"/api/users/{user.username}", 200, json=user, headers=headers)
    r = client.get_typed(f"/api/users/{user.username}", 200, User, headers=headers)
    assert user.email == r.email

    # DELETE
    client.delete(f"/api/users/{user.username}", 200, headers=headers)
    client.get(f"/api/users/{user.username}", 404, headers=headers)
```

## 1.2 Authentication & authorization

### Roles

```python
from enum import StrEnum


class Role(StrEnum):
    ADMIN = "admin"


ROLE_DESCRIPTIONS = {
    Role.ADMIN: "Admin",
}
```

### Config - auth

```python
    auth: AuthConfig = AuthConfig(jwt_secret_key="")
```

### Dependencies - AuthServiceDep, AuthTokenDep, TokenPayloadDep, Authorize

```python
def get_auth_service(app_state: AppStateDep) -> AuthService:
    return AuthService(
        storage_factory=app_state.async_factory,
        user_service=app_state.user_service,
        auth_config=app_state.config.auth,
        email_sender_service=None,
        reset_mail_template=None,
    )


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]


AuthTokenDep = Annotated[str, Depends(OAuth2PasswordBearer(tokenUrl="api/login"))]


async def decode_token(auth_service: AuthServiceDep, token: AuthTokenDep) -> TokenPayload:
    return await auth_service.decode_token(token)


TokenPayloadDep = Annotated[TokenPayload, Depends(decode_token)]


class Authorize:
    """Dependency for authorizing users based on their role."""

    def __init__(self, required_role: Role | None = None):
        self.required_role = required_role

    def __call__(self, token_payload: TokenPayloadDep) -> bool:
        if not self.required_role or self.required_role.value in token_payload.roles:
            return True
        else:
            raise InsufficientPermissionsError()
```

### Auth router

```python
from typing import Annotated, List

from ampf.auth import ChangePasswordData, Tokens
from core.roles import ROLE_DESCRIPTIONS, Role
from dependencies import AuthServiceDep, AuthTokenDep, TokenPayloadDep
from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel

router = APIRouter(tags=["Authentication"])

UserFormDataDep = Annotated[OAuth2PasswordRequestForm, Depends()]


@router.post("/login")
async def login(auth_service: AuthServiceDep, form_data: UserFormDataDep) -> Tokens:
    return await auth_service.authorize(form_data.username, form_data.password)


@router.post("/logout")
async def logout(auth_service: AuthServiceDep, refresh_token: AuthTokenDep) -> None:
    await auth_service.add_to_black_list(refresh_token)


@router.post("/refresh-token")
async def refresh_token(auth_service: AuthServiceDep, refresh_token: AuthTokenDep) -> Tokens:
    return await auth_service.refresh_token(refresh_token)


@router.post("/change-password")
async def change_password(
    auth_service: AuthServiceDep,
    payload: ChangePasswordData,
    token_payload: TokenPayloadDep,
) -> None:
    await auth_service.change_password(token_payload.sub, payload.old_password, payload.new_password)


class RoleDto(BaseModel):
    name: str
    description: str


@router.get("/roles")
def get_roles() -> List[RoleDto]:
    return [RoleDto(name=role.value, description=ROLE_DESCRIPTIONS[role]) for role in Role]
```

```python
app.include_router(auth.router, prefix="/api")
```

### Add authentication & authorization checking

Add `Authorize` dependency to routers or endpoints:

- no `Authorize` dependency - available for all users
- `Authorize()` __without__ role - available for all authenticated users
- `Authorize(Role.ADMIN)` __with__ role - available for users with this role

```python
app.include_router(auth.router, prefix="/api")
app.include_router(config.router, prefix="/api/config")
app.include_router(users.router, prefix="/api/users", dependencies=[Depends(Authorize(Role.ADMIN))])
app.include_router(prompts.router, prefix="/api/prompts", dependencies=[Depends(Authorize())])
```

### Tests - auth

Modify & add fixtures:

```python
@pytest.fixture
def config(tmp_path) -> AppConfig:
    config = AppConfig(
        ...
        default_user=DefaultUser(username="test", email="test@test.com", password="test", roles=["admin"]),
        auth=AuthConfig(jwt_secret_key="test-test-test-test-test-test-test"),
    )
    return config


@pytest_asyncio.fixture
async def tokens(async_factory: BaseAsyncFactory, client: ApiTestClient) -> Tokens:
    # Clear token_black_list
    await async_factory.create_compact_storage("token_black_list", TokenExp, "token").drop()
    # Login
    return client.post_typed("/api/login", 200, Tokens, data={"username": "test", "password": "test"})


@pytest.fixture
def headers(tokens: Tokens) -> dict[str, str]:
    return {"Authorization": f"Bearer {tokens.access_token}"}
```

Remove empty `header()` fixture from `test_users.py` to use the above one.

#### tests/unit/routers/test_auth.py

```python
import time

from ampf.auth import Tokens
from routers.auth import RoleDto


def test_login_ok(client):
    # When: Default user logs in
    response = client.post(
        "/api/login",
        data={"username": "test", "password": "test"},
    )
    # Then: The response status code is 200
    assert response.status_code == 200
    r = response.json()
    # Then: The response contains access_token, refresh_token and token_type
    assert "access_token" in r
    assert "refresh_token" in r
    assert "token_type" in r
    assert r["token_type"] == "Bearer"


def test_login_wrong_password(client):
    # When: Default user logs in with wrong password
    response = client.post(
        "/api/login",
        data={"username": "test", "password": "wrong"},
    )
    # Then: The response status code is 401
    assert response.status_code == 401


def test_login_wrong_username(client):
    # When: Default user logs in with wrong password
    response = client.post(
        "/api/login",
        data={"username": "admin@test", "password": "test"},
    )
    # Then: The response status code is 401
    assert response.status_code == 401


def test_logout(client, tokens: Tokens):
    # When: Default user logs out
    response = client.post(
        "/api/logout",
        headers={"Authorization": f"Bearer {tokens.refresh_token}"},
    )
    # Then: The response status code is 200
    assert response.status_code == 200


def test_refresh_token(client, tokens: Tokens):
    # Wait for 1 second
    time.sleep(1)
    # When: Default user refreshes token
    response = client.post(
        "/api/refresh-token",
        headers={"Authorization": f"Bearer {tokens.refresh_token}"},
    )
    # Then: The response status code is 200
    assert response.status_code == 200
    r = response.json()
    # Then: The response contains access_token, refresh_token and token_type
    assert "access_token" in r
    assert "refresh_token" in r
    assert "token_type" in r
    assert r["token_type"] == "Bearer"
    assert r["access_token"] != tokens.access_token
    assert r["refresh_token"] != tokens.refresh_token


def test_change_password(client, tokens: Tokens):
    # When: Default user changes password
    response = client.post(
        "/api/change-password",
        headers={"Authorization": f"Bearer {tokens.access_token}"},
        json={"old_password": "test", "new_password": "new_test"},
    )
    # Then: The response status code is 200
    assert response.status_code == 200
    # When: Default user logs in with new password
    response = client.post(
        "/api/login",
        data={"username": "test", "password": "new_test"},
    )
    # Then: The response status code is 200
    assert response.status_code == 200
    # Clean up
    assert (
        200
        == client.post(
            "/api/change-password",
            headers={"Authorization": f"Bearer {tokens.access_token}"},
            json={"old_password": "new_test", "new_password": "test"},
        ).status_code
    )


def test_get_roles(client):
    # When: Get roles
    roles = client.get_typed_list("/api/roles", 200, RoleDto)
    # Then: At least admin is returned
    assert len(roles) > 0
    assert "admin" in [role.name for role in roles]
```

## 1.3 Password reset functionality

### Config SMTPServer & ResetPasswordMail

Add to `AppConfig`.

```python
    smtp: SmtpConfig = SmtpConfig()
    reset_password_mail: ResetPasswordMailConfig = ResetPasswordMailConfig()
```

### Dependencies

Update `AuthServiceDep`.

```python
def get_auth_service(app_state: AppStateDep) -> AuthService:
    reset_mail_template = EmailTemplate(
        sender=app_state.config.reset_password_mail.sender,
        subject=app_state.config.reset_password_mail.subject,
        body_template=app_state.config.reset_password_mail.body_template,
    )
    email_sender = SmtpEmailSender(
        host=app_state.config.smtp.host,
        port=app_state.config.smtp.port,
        username=app_state.config.smtp.username,
        password=app_state.config.smtp.password,
        use_ssl=app_state.config.smtp.use_ssl,
    )
    return AuthService(
        storage_factory=app_state.async_factory,
        user_service=app_state.user_service,
        auth_config=app_state.config.auth,
        email_sender_service=email_sender,
        reset_mail_template=reset_mail_template,
    )


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]
```

#### app/routers/auth.py

Add endpoints.

```python
@router.post("/reset-password-request")
async def reset_password_request(auth_service: AuthServiceDep, rpr: ResetPasswordRequest):
    await auth_service.reset_password_request(rpr.email)


@router.post("/reset-password")
async def reset_password(auth_service: AuthServiceDep, rp: ResetPassword):
    await auth_service.reset_password(rp.email, rp.reset_code, rp.new_password)
```

## 2.1 User authentication service & interceptor

The `AuthService` responses for:

- login (Sign In) user
- logout (Sign Out) user
- decode tokens
- store tokens and user data
- validate user roles
- refresh tokens
- change user's password

### AuthService

#### src/app/core/auth/auth.service.ts

```typescript
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Router } from '@angular/router';
import { jwtDecode } from 'jwt-decode';
import { BehaviorSubject, catchError, filter, finalize, Observable, take, tap, throwError } from 'rxjs';

export interface Credentials {
    username: string;
    password: string;
}

export interface Tokens {
    access_token: string;
    refresh_token: string;
}

@Injectable({
    providedIn: 'root'
})
export class AuthService {
    username?: string;
    access_token?: string;
    refresh_token?: string;
    user_email?: string;
    roles: string[] = [];
    user_photo_url?: string;
    store_token = false;
    redirectUrl: string | undefined;

    constructor(private http: HttpClient, private router: Router) { }

    /**
     * Login user with username and password
     * @param credentials 
     * @returns 
     */
    login(credentials: Credentials, store_token = false): Observable<any> {
        const formData = new FormData();
        formData.append('username', credentials.username);
        formData.append('password', credentials.password);
        this.store_token = store_token;
        return this.http.post<Tokens>('/api/login', formData).pipe(
            tap((value) => this.setData(value))
        );
    }

    /**
 * Logout user from server, clear data and redirect to login page
 * @returns Observable<void>
 */
    logout(): Observable<void> {
        const headers = new HttpHeaders({ 'Authorization': `Bearer ${this.refresh_token}` });
        return this.http.post<void>('/api/logout', {}, { headers: headers }).pipe(tap({
            finalize: () => {
                this.cleanData();
                this.router.navigate(['/login']);
            }
        }));
    }

    /**
     * Set tokens, user data decoded from token and
     * redirects if necessery
     * @param tokens 
     */
    setData(tokens: Tokens): void {
        this.setTokens(tokens);
        this.decodeToken(tokens.access_token);
        if (this.redirectUrl) {
            this.router.navigate([this.redirectUrl]);
            this.redirectUrl = undefined;
        } else {
            this.router.navigateByUrl('/'); // Redirect to home page after login if no redirectUrl is set
        }
    }

    /**
     * Clear user data and remove tokens from local storage
     */
    cleanData(): void {
        this.access_token = undefined;
        this.username = undefined;
        this.user_email = undefined;
        this.roles = [];
        this.user_photo_url = undefined;
        localStorage.removeItem("access_token");
        localStorage.removeItem("refresh_token");
    }

    /**
     * Check if user is logged in
     * @returns boolean
     */
    isAuthenticated(): boolean {
        if (this.username)
            return true;
        this.access_token = localStorage.getItem("access_token") ?? undefined
        this.refresh_token = localStorage.getItem("refresh_token") ?? undefined
        if (this.access_token) {
            this.store_token = true;
            this.decodeToken(this.access_token);
            return true;
        }
        return false;
    }

    hasRole(role: string): boolean {
        return this.roles.includes(role);
    }

    hasAnyRole(requiredRoles: string[]): boolean {
        return requiredRoles.some(role => this.roles.includes(role));
    }

    hasAllRoles(requiredRoles: string[]): boolean {
        return requiredRoles.every(role => this.roles.includes(role));
    }
    /**
     * Decode JWT token and set user data
     * @param token JWT token
     */
    private decodeToken(token: string): void {
        const payload: any = jwtDecode(token);
        this.username = payload.sub;
        this.user_email = payload.email;
        this.roles = payload.roles;
        this.user_photo_url = payload.picture;
    }

    /**
     * Set tokens (also in browser local storage)
     * @param tokens 
     */
    setTokens(tokens: Tokens): void {
        this.access_token = tokens.access_token;
        this.refresh_token = tokens.refresh_token
        console.log(this.store_token)
        if (this.store_token) {
            localStorage.setItem("access_token", this.access_token);
            localStorage.setItem("refresh_token", this.refresh_token);
        }
    }

    resetPasswordRequest(email: string): Observable<void> {
        return this.http.post<void>("/api/reset-password-request", { email: email });
    }

    resetPassword(email: string, reset_code: string, new_password: string): Observable<void> {
        return this.http.post<void>("/api/reset-password", {
            email: email,
            reset_code: reset_code,
            new_password: new_password
        });
    }

    changePassword(old_password: string, new_password: string): Observable<void> {
        return this.http.post<void>('/api/change-password', {
            old_password: old_password,
            new_password: new_password
        });
    }
    private isRefreshing = false;
    private refreshTokenSubject: BehaviorSubject<Tokens | null> = new BehaviorSubject<Tokens | null>(null);

    refreshToken(): Observable<Tokens> {
        if (this.isRefreshing) {
            // If already refreshing, wait for new access token
            return this.refreshTokenSubject.pipe(
                filter((token): token is Tokens => token !== null),
                take(1)
            );
        }

        this.isRefreshing = true;
        this.refreshTokenSubject.next(null);

        const headers = new HttpHeaders({
            'Authorization': `Bearer ${this.refresh_token}`
        });

        return this.http.post<Tokens>('/api/refresh-token', {}, { headers }).pipe(
            tap(tokens => {
                this.setTokens(tokens);
                this.decodeToken(tokens.access_token);
                this.refreshTokenSubject.next(tokens);
            }),
            catchError(err => {
                this.cleanData();
                this.router.navigate(['/login']);
                return throwError(() => err);
            }),
            finalize(() => {
                this.isRefreshing = false;
            })
        );
    }
}
```

### AuthInterceptor

The `AuthInterceptor`checks if user is authenticated, adds authorization token to all requests and rehreshes the token.

#### src/app/core/auth/auth.interceptor.ts

```typescript
import { HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { Router } from '@angular/router';
import { catchError, switchMap } from 'rxjs';
import { AuthService } from './auth.service';

const EXCLUDED_ROUTES = [
    '/api/ping',
    '/api/config',
    '/api/login',
    '/api/logout',
    '/api/refresh-token',
    '/api/reset-password-request',
    '/api/reset-password'
];


export const authInterceptor: HttpInterceptorFn = (req, next) => {
    if (EXCLUDED_ROUTES.includes(req.url)) {
        return next(req);
    }
    const authService = inject(AuthService);
    const router = inject(Router);
    if (authService.isAuthenticated()) {
        const headers = req.headers.set('Authorization', `Bearer ${authService.access_token}`);
        req = req.clone({ headers });
        return next(req).pipe(
            catchError(err => {
                if (err.status === 401) {
                    return authService.refreshToken().pipe(
                        switchMap(newTokens => {
                            // Retry original request with new token
                            const newReq = req.clone({
                                setHeaders: { Authorization: `Bearer ${newTokens.access_token}` }
                            });
                            return next(newReq);
                        }),
                        catchError(refreshErr => {
                            if (refreshErr.status === 401) {
                                console.warn('Refresh token error:', refreshErr);
                                authService.cleanData();
                                router.navigate(['/login']);
                            }
                            throw refreshErr;
                        })
                    );
                };
                throw err;
            }));
    } else {
        router.navigate(['/login']);
        throw new Error('Unauthorized');
    }
};
```

Add `authInterceptor` to `app.config.ts`.

#### src/app/app.config.ts

```typescript
export const appConfig: ApplicationConfig = {
  providers: [
    ...
    provideHttpClient(withInterceptors([authInterceptor])),
    ...
    }),
  ]
};
```

### authGuard

```typescript
import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { AuthService } from './auth.service';
import { MatSnackBar } from '@angular/material/snack-bar';

export const authGuard: CanActivateFn = (route, state) => {
    const authService = inject(AuthService);
    const router = inject(Router);

    if (!authService.isAuthenticated()) {
        authService.redirectUrl = state.url
        router.navigate(['/login']);
        return false;
    } else if (route.data['roles'] && !authService.hasAnyRole(route.data['roles'])) {
        const snackBar = inject(MatSnackBar);
        snackBar.open('Unauthorized access', 'Close');
        router.navigate(['/']);
        return false;
    } else {
        return true;
    }
};
```

## 2.2 User login form

### LoginFormComponent

#### src/app/core/auth/login-form/login-form.component.html

```html
<div class="centered-form">
    <form class="center-content" (ngSubmit)="onSubmit()" #loginForm="ngForm">
        <mat-card>
            <mat-card-header>
                <mat-card-title>Logowanie</mat-card-title>
            </mat-card-header>
            <mat-card-content>
                <mat-form-field class="full-width">
                    <mat-label>User name</mat-label>
                    <input matInput type="text" name="username" [(ngModel)]="credentials.username" required
                        autocomplete="username" autofocus>
                </mat-form-field>
                <mat-form-field class="full-width">
                    <mat-label>Password</mat-label>
                    <input matInput type="password" name="password" [(ngModel)]="credentials.password" required
                        autocomplete="current-password">
                </mat-form-field>
                <div class="row">
                    <div class="col">
                        <div class="full-width">
                            <mat-checkbox name="store_token" [(ngModel)]="store_token">Remember me</mat-checkbox>
                        </div>
                    </div>
                </div>
            </mat-card-content>
            <mat-card-actions align="end">
                <button mat-raised-button type="button" routerLink="/reset-password-request">Password reset</button>
                <button mat-raised-button color="primary" type="submit"
                    [disabled]="!loginForm.form.valid">Sign in</button>
            </mat-card-actions>
        </mat-card>
    </form>
</div>
<div class="footer-version">v. {{version$ | async}}</div>
```

#### src/app/core/auth/login-form/login-form.component.ts

```typescript
import { Component } from '@angular/core';
import { Router, RouterModule } from '@angular/router';
import { AuthService } from '../auth.service';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { FormsModule } from '@angular/forms';
import { CommonModule } from '@angular/common';
import { MatButton } from '@angular/material/button';
import { MatInputModule } from '@angular/material/input';
import { MatSnackBar } from '@angular/material/snack-bar';
import { Observable } from 'rxjs';
import { ConfigService } from '../../config.service';

@Component({
    selector: 'app-login-form',
    imports: [
        CommonModule,
        FormsModule,
        MatCardModule,
        MatInputModule,
        MatButton,
        MatFormFieldModule,
        MatCheckboxModule,
        RouterModule,
    ],
    templateUrl: './login-form.component.html',
    styleUrl: './login-form.component.scss'
})
export class LoginFormComponent {
    credentials = { username: '', password: '' };
    store_token = false;

    version$: Observable<string>;

    constructor(private configService: ConfigService, private authService: AuthService, private router: Router, private snackBar: MatSnackBar) {
        this.version$ = this.configService.getConfigValue$("version");
        if (authService.isAuthenticated())
            this.router.navigate(['/']);
    }

    onSubmit() {
        this.authService.login(this.credentials, this.store_token).subscribe({
            error: (err) => {
                if (err.status == 401)
                    this.snackBar.open('Wrong username or password', 'Close', { duration: 1500 });
                else {
                    console.warn(err.message);
                    this.snackBar.open(err.message, 'Close');
                }
            }
        });
    }
}
```

### Login form routing

Add routing to login form.

#### src/app/app.routes.ts

```typescript
...
{ path: 'login', title: "Personal AI Assistant - Sign In", loadComponent: () => import('./core/auth/login-form/login-form.component').then(m => m.LoginFormComponent) },
...
```

## 2.3 Frontend - User management (CRUD) & authorization

### UserService & RoleService

`UserService` is just a CURD service with extra `changePassword` method.
`RoleService` returns list of roles.

#### src/app/core/users/user.service.ts

```typesript
import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';

export interface User {
    username: string;
    email?: string | null;
    name?: string | null;
    disabled?: boolean;
    roles?: string[];
    picture?: string | null;
    password?: string | null; // Only for creation/update, not typically returned
}

export interface UserHeader {
    username: string;
    email?: string | null;
    name?: string | null;
    disabled?: boolean;
    roles?: string[];
    picture?: string | null;
}

@Injectable({
    providedIn: 'root'
})
export class UserService {
    public readonly endpoint = '/api/users';

    constructor(private httpClient: HttpClient) { }

    getAll(): Observable<UserHeader[]> {
        return this.httpClient.get<UserHeader[]>(this.endpoint);
    }

    create(body: User): Observable<User> {
        return this.httpClient.post<User>(this.endpoint, body);
    }

    get(username: string): Observable<User> {
        return this.httpClient.get<User>(`${this.endpoint}/${username}`);
    }

    update(username: string, body: User): Observable<User> {
        return this.httpClient.put<User>(`${this.endpoint}/${username}`, body);
    }

    changePassword(username: string, password: string): Observable<void> {
        return this.httpClient.patch<void>(`${this.endpoint}/${username}/change-password`, { password: password });
    }

    delete(username: string): Observable<void> {
        return this.httpClient.delete<void>(`${this.endpoint}/${username}`);
    }
}
```

#### src/app/core/role.service.ts

```typescript
import { Injectable } from '@angular/core';
import { BaseDictionaryService } from '../../shared/base-dictionary.service';

export interface RoleDto {
  name: string;
  description: string;
}


@Injectable({
  providedIn: 'root'
})
export class RoleService extends BaseDictionaryService<RoleDto> {
  protected override endpoint = 'roles';
  protected override keyName: keyof RoleDto = 'name';
}
```

### UserTableComponent

#### src/app/core/users/user-table/user-table.component.html

```html
<app-main-toolbar />
<div class="table-filter">
    <mat-form-field>
        <mat-label>Filter</mat-label>
        <input matInput (keyup)="dataSource.applyFilter($event)" placeholder="Ex. Mia" #input>
    </mat-form-field>
    <button mat-fab color="primary" [routerLink]="['/users', '__NEW__']">
        <mat-icon>add</mat-icon>
    </button>
</div>

<div class="mat-elevation-z8">
    @if (dataSource.isLoading) {
    <div class="loading-overlay">
        <mat-progress-spinner mode="indeterminate"></mat-progress-spinner>
    </div>
    }
    <table mat-table [dataSource]="dataSource" matSort>

        <!-- username Column -->
        <ng-container matColumnDef="username">
            <th mat-header-cell *matHeaderCellDef mat-sort-header> Username </th>
            <td mat-cell *matCellDef="let row"> {{row.username}} </td>
        </ng-container>

        <!-- email Column -->
        <ng-container matColumnDef="email">
            <th mat-header-cell *matHeaderCellDef mat-sort-header> Email </th>
            <td mat-cell *matCellDef="let row"> {{row.email}} </td>
        </ng-container>

        <!-- name Column -->
        <ng-container matColumnDef="name">
            <th mat-header-cell *matHeaderCellDef mat-sort-header> Name </th>
            <td mat-cell *matCellDef="let row"> {{row.name}} </td>
        </ng-container>

        <!-- disabled Column -->
        <ng-container matColumnDef="disabled">
            <th mat-header-cell *matHeaderCellDef mat-sort-header> Disabled </th>
            <td mat-cell *matCellDef="let row"> {{row.disabled}} </td>
        </ng-container>

        <!-- roles Column -->
        <ng-container matColumnDef="roles">
            <th mat-header-cell *matHeaderCellDef mat-sort-header> Roles </th>
            <td mat-cell *matCellDef="let row"> {{row.roles}} </td>
        </ng-container>

        <!-- picture Column -->
        <ng-container matColumnDef="actions">
            <th mat-header-cell *matHeaderCellDef mat-sort-header></th>
            <td mat-cell *matCellDef="let row">
                @if (currentUsername != row.username) {
                <button mat-icon-button color="primary" (click)="editRow(row); $event.stopPropagation();"
                    matTooltip="Edit">
                    <mat-icon>edit</mat-icon>
                </button>
                <button mat-icon-button color="primary" (click)="changePasswordRow(row); $event.stopPropagation();"
                    matTooltip="Change user password">
                    <mat-icon>key</mat-icon>
                </button>
                <button mat-icon-button color="warn" (click)="deleteRow(row); $event.stopPropagation();"
                    matTooltip="Delete">
                    <mat-icon>delete</mat-icon>
                </button>
                }
            </td>
        </ng-container>

        <tr mat-header-row *matHeaderRowDef="displayedColumns"></tr>
        <tr mat-row *matRowDef="let row; columns: displayedColumns;" (click)="onClickRow(row)" class="clickable-row">
        </tr>
    </table>

    <mat-paginator [pageSizeOptions]="[5, 10, 20]" showFirstLastButtons></mat-paginator>
</div>
```

#### src/app/core/users/user-table/user-table.component.ts

```typescript
import { CommonModule } from '@angular/common';
import { AfterViewInit, Component, ViewChild } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatDialog } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatPaginator, MatPaginatorModule } from '@angular/material/paginator';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatSnackBar } from '@angular/material/snack-bar';
import { MatSort, MatSortModule } from '@angular/material/sort';
import { MatTable, MatTableModule } from '@angular/material/table';
import { MatTooltipModule } from '@angular/material/tooltip';
import { Router, RouterModule } from '@angular/router';
import { MatTableDataSourceClientSide } from '../../../shared/mat-table-data-source-client-side';
import { SimpleDialogComponent } from '../../../shared/simple-dialog/simple-dialog.component';
import { MainToolbarComponent } from "../../main-toolbar/main-toolbar.component";
import { UserHeader, UserService } from '../user.service';

@Component({
    selector: 'app-user-table',
    imports: [
        CommonModule,
        RouterModule,
        MatTableModule,
        MatPaginatorModule,
        MatSortModule,
        FormsModule,
        MatFormFieldModule,
        MatInputModule,
        MatTooltipModule,
        MatButtonModule,
        MatIconModule,
        MatProgressSpinnerModule,
        MainToolbarComponent
    ],
    templateUrl: './user-table.component.html',
    styleUrl: './user-table.component.scss'
})
export class UserTableComponent implements AfterViewInit {
    @ViewChild(MatTable) table!: MatTable<UserHeader>;
    @ViewChild(MatPaginator) paginator!: MatPaginator;
    @ViewChild(MatSort) sort!: MatSort;

    dataSource: MatTableDataSourceClientSide<UserHeader>;
    displayedColumns: string[] = ['username', 'email', 'name', 'disabled', 'roles', 'actions'];
    currentUsername: string | undefined;

    constructor(
        private router: Router,
        private dialog: MatDialog,
        private snackbar: MatSnackBar,
        private userService: UserService,
    ) {
        this.dataSource = new MatTableDataSourceClientSide<UserHeader>(this.userService.endpoint);
        // this.currentUsername = authService.username;

    }

    ngAfterViewInit(): void {
        this.dataSource.setPaginatorAndSort(this.paginator, this.sort);
    }

    onClickRow(row: UserHeader): void {
        this.editRow(row);
    }

    editRow(row: UserHeader): void {
        this.router.navigate(['/users', row.username]);
    }

    changePasswordRow(row: UserHeader): void {
        this.router.navigate(['/users', row.username, 'change-password']);
    }

    deleteRow(row: UserHeader): void {
        this.dialog
            .open(SimpleDialogComponent, {
                data: {
                    title: 'Delete user',
                    message: `Are you sure you want to delete user "<b>${row.username}</b>"?`,
                    confirm: true
                }
            })
            .afterClosed().subscribe(result => {
                if (result && row.username)
                    this.userService.delete(row.username).subscribe({
                        next: () => {
                            this.dataSource.data = this.dataSource.data.filter(item => item.username !== row.username);
                            this.table.renderRows();
                            this.snackbar.open(`User "${row.username}" deleted successfully`, 'Close', { duration: 1500 });
                        },
                        error: (error) => {
                            this.snackbar.open(`Error deleting user "${row.username}": ${error.message}`, 'Close', { duration: 3000 });
                        }
                    });
            });
    }
}
```

### UserEditComponent

#### src/app/core/users/user-edit/user-edit.component.html

```html
<app-main-toolbar />
<form class="full-screen-container" [formGroup]="form" (ngSubmit)="save()">
    <mat-card>
        <mat-card-header>
            <mat-card-title>{{ isCreateMode ? 'New User' : 'Edit User: ' + username }}</mat-card-title>
        </mat-card-header>
        <mat-card-content>
            <div class="container">
                <mat-form-field appearance="fill" class="full-width">
                    <mat-label>Username</mat-label>
                    <input matInput formControlName="username" (blur)="onUsernameBlur()">
                    @if (form.get('username')?.hasError('required') && form.get('username')?.touched) {
                    <mat-error> Username is required </mat-error>
                    }
                </mat-form-field>

                <mat-form-field appearance="fill" class="full-width">
                    <mat-label>Email</mat-label>
                    <input matInput formControlName="email" type="email">
                    @if (form.get('email')?.hasError('required') && form.get('email')?.touched) {
                    <mat-error> Email is required </mat-error>
                    }
                    @if (form.get('email')?.hasError('email') && form.get('email')?.touched) {
                    <mat-error> Email is invalid </mat-error>
                    }
                </mat-form-field>

                <mat-form-field appearance="fill" class="full-width">
                    <mat-label>Name</mat-label>
                    <input matInput formControlName="name">
                    @if (form.get('name')?.hasError('required') && form.get('name')?.touched) {
                    <mat-error> Name is required </mat-error>
                    }
                </mat-form-field>

                <mat-form-field appearance="fill" class="full-width">
                    <mat-label>Roles</mat-label>
                    <mat-select formControlName="roles" multiple>
                        @for (role of roles; track role.name) {
                        <mat-option [value]="role.name" [matTooltip]="role.description">{{ role.name }}</mat-option>
                        }
                    </mat-select>
                </mat-form-field>

                <mat-checkbox formControlName="disabled">Disabled</mat-checkbox>
                @if (isCreateMode) {
                <mat-form-field appearance="fill" class="full-width">
                    <mat-label>Password</mat-label>
                    <input matInput formControlName="password" type="password">
                </mat-form-field>
                }
            </div>
        </mat-card-content>
        <mat-card-actions>
            <button type="button" mat-button (click)="cancel()" [disabled]="isLoading">Cancel</button>
            <button type="submit" mat-raised-button color="primary" [disabled]="form.invalid || isLoading">
                @if (isLoading) {
                <mat-spinner diameter="20"></mat-spinner>
                } @else {
                {{ isCreateMode ? 'Create' : 'Save' }}
                }
            </button>
        </mat-card-actions>
    </mat-card>
</form>
```

#### src/app/core/users/user-edit/user-edit.component.ts

```typescript
import { CommonModule, Location } from '@angular/common';
import { Component, OnInit } from '@angular/core';
import { FormBuilder, FormGroup, FormsModule, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatSnackBar } from '@angular/material/snack-bar';
import { ActivatedRoute, Router } from '@angular/router';
import { finalize } from 'rxjs/operators';
import { User, UserService } from '../user.service';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatOptionModule } from '@angular/material/core';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatSelectModule } from '@angular/material/select';
import { RoleDto, RoleService } from '../../auth/role.service';
import { MainToolbarComponent } from "../../main-toolbar/main-toolbar.component";

@Component({
    selector: 'app-user-edit',
    imports: [
    CommonModule,
    FormsModule,
    ReactiveFormsModule,
    MatCardModule,
    MatFormFieldModule,
    MatInputModule,
    MatCheckboxModule,
    MatSelectModule,
    MatOptionModule,
    MatTooltipModule,
    MatButtonModule,
    MatIconModule,
    MatProgressSpinnerModule,
    MainToolbarComponent
],
    templateUrl: './user-edit.component.html',
    styleUrls: ['./user-edit.component.scss']
})
export class UserEditComponent implements OnInit {
    form!: FormGroup;
    isCreateMode: boolean = true;
    username: string | null = null;
    isLoading: boolean = false;

    roles: RoleDto[] = [];

    constructor(
        private fb: FormBuilder,
        private route: ActivatedRoute,
        private location: Location,
        private roleService: RoleService,
        private userService: UserService,
        private snackBar: MatSnackBar
    ) { }

    ngOnInit(): void {
        this.username = this.route.snapshot.paramMap.get('username');
        this.isCreateMode = this.username === '__NEW__';

        this.roleService.getAll().subscribe({
            next: roles => this.roles = roles,
            error: error => {
                this.snackBar.open('Error loading roles.', 'Close', { duration: 3000 });
                console.error('Error loading roles:', error);
            }
        });

        this.form = this.fb.group({
            username: [{ value: '', disabled: !this.isCreateMode }, Validators.required],
            email: ['', [Validators.required, Validators.email]],
            name: ['', Validators.required],
            disabled: [false],
            roles: [[]],
            password: [''] // Only for creation/update, not typically returned
        });

        if (!this.isCreateMode && this.username) {
            this.isLoading = true;
            this.userService.get(this.username).pipe(
                finalize(() => this.isLoading = false)
            ).subscribe({
                next: (user: User) => {
                    this.form.patchValue(user);
                    // Clear password field for security, as it's not meant to be displayed
                    this.form.get('password')?.setValue('');
                },
                error: error => {
                    this.snackBar.open('Error loading user data.', 'Close', { duration: 3000 });
                    console.error('Error loading user:', error);
                    this.location.back();
                }
            });
        }
    }

    save(): void {
        if (this.form.invalid) {
            this.form.markAllAsTouched();
            this.snackBar.open('Please correct the form errors.', 'Close', { duration: 3000 });
            return;
        }

        this.isLoading = true;
        const userValue: User = this.form.getRawValue(); // Use getRawValue to include disabled fields

        if (this.isCreateMode) {
            this.userService.create(userValue).pipe(
                finalize(() => this.isLoading = false)
            ).subscribe({
                next: () => {
                    this.snackBar.open('User created successfully!', 'Close', { duration: 3000 });
                    this.location.back();
                },
                error: error => {
                    this.snackBar.open('Error creating user.', 'Close', { duration: 3000 });
                    console.error('Error creating user:', error);
                }
            });
        } else if (this.username) {
            if (!userValue.password) {
                delete userValue.password;
            }
            this.userService.update(this.username, userValue).pipe(
                finalize(() => this.isLoading = false)
            ).subscribe({
                next: () => {
                    this.snackBar.open('User updated successfully!', 'Close', { duration: 3000 });
                    this.location.back();
                },
                error: error => {
                    this.snackBar.open('Error updating user.', 'Close', { duration: 3000 });
                    console.error('Error updating user:', error);
                }
            });
        }
    }

    cancel(): void {
        this.location.back();
    }

    onUsernameBlur() {
        const usernameValue = this.form.get('username')?.value;
        if (usernameValue && usernameValue.includes('@')) {
            this.form.patchValue({
                email: usernameValue.toLowerCase()
            });
        }
    }
}
```

### Routes & menu

Only users with `admin` role can view and edit users.

#### src/app/app.routes.ts

```typescript
import { Routes } from '@angular/router';

export const routes: Routes = [
    ...
    {
        path: 'users', title: "Użytkownicy", canActivate: [authGuard], data: { roles: ['admin'] },
        loadComponent: () => import('./core/users/user-table/user-table.component').then(m => m.UserTableComponent)
    },
    {
        path: 'users/:username', title: "Edycja użytkownika", canActivate: [authGuard], data: { roles: ['admin'] },
        loadComponent: () => import('./core/users/user-edit/user-edit.component').then(m => m.UserEditComponent)
    },
    ...
];
```

#### src/app/core/main-toolbar/main-toolbbar.component.html

```html
    <mat-menu #menu="matMenu">
        ...
        @if (authService.hasRole("admin")) {
        <button mat-menu-item routerLink="/users" routerLinkActive="active-link">
            <mat-icon>manage_accounts</mat-icon>
            <span>Users</span>
        </button>
        }
    </mat-menu>
    ...
```

The same solution with `authGuard` and `authService` should be used with other features.

## 2.4 Change password & logout

### ChangePasswordComponent

#### src/app/core/users/change-password/change-password.component.html

```html
<div class="centered-form">
    <form (ngSubmit)="onSubmit()" [formGroup]="form">
        <mat-card>
            <mat-card-header>
                @if (username) {
                <mat-card-title>Zmiana hasła dla <b>{{ username }}</b></mat-card-title>
                } @else {
                <mat-card-title>Zmiana hasła</mat-card-title>
                }
            </mat-card-header>
            <mat-card-content>
                @if (!username) {
                <mat-form-field class="full-width">
                    <mat-label>Aktualne hasło</mat-label>
                    <input matInput type="password" formControlName="old_password" required>
                    @if (form.controls['old_password'].hasError('required')) {
                    <mat-error>Hasło jest <strong>wymagane</strong></mat-error>
                    }
                </mat-form-field>
                }
                <mat-form-field class="full-width">
                    <mat-label>Nowe hasło</mat-label>
                    <input matInput type="password" formControlName="new_password" required>
                    @if (form.controls['new_password'].hasError('required')) {
                    <mat-error>Hasło jest <strong>wymagane</strong></mat-error>
                    }
                    @if (form.controls['new_password'].hasError('passwordStrength')) {
                    <mat-error>Hasło zawierać przynajmniej jedną <strong>małą i dużą literę oraz
                            cyfrę</strong></mat-error>
                    }
                    @if (form.controls['new_password'].hasError('minlength')) {
                    <mat-error>Hasło musi mieć minimum <strong>8 znaków</strong></mat-error>
                    }
                </mat-form-field>
                <mat-form-field class="full-width">
                    <mat-label>Ponownie nowe hasło</mat-label>
                    <input matInput type="password" formControlName="new_password2" required>
                    @if (form.controls['new_password2'].hasError('required')) {
                    <mat-error>Hasło jest <strong>wymagane</strong></mat-error>
                    }
                    @if (form.controls['new_password2'].hasError('equals')) {
                    <mat-error>Podane hasła <strong>różnią</strong> się</mat-error>
                    }
                </mat-form-field>
            </mat-card-content>
            <mat-card-actions>
                <button mat-button type="button" routerLink="/">Anuluj</button>
                <button mat-raised-button color="primary" type="submit" [disabled]="!form.valid">Zmień</button>
            </mat-card-actions>
        </mat-card>
    </form>
</div>
```

#### src/app/core/users/change-password/change-password.component.ts

```typescript
import { Component, inject, OnInit } from '@angular/core';
import { AbstractControl, FormBuilder, ReactiveFormsModule, ValidationErrors, ValidatorFn, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSnackBar } from '@angular/material/snack-bar';
import { ActivatedRoute, Router, RouterModule } from '@angular/router';
import { AuthService } from '../auth.service';
import { passwordStrengthValidator, newPasswordEqualsValidator } from '../../validators';
import { User, UserService } from '../../users/user.service';

@Component({
    selector: 'app-change-password-form',
    imports: [
        RouterModule,
        ReactiveFormsModule,
        MatCardModule,
        MatFormFieldModule,
        MatInputModule,
        MatButtonModule,
    ],
    templateUrl: './change-password-form.component.html',
    styleUrl: './change-password-form.component.scss'
})
export class ChangePasswordFormComponent implements OnInit {
    private fb = inject(FormBuilder);
    form = this.fb.group({
        old_password: ['', Validators.required],
        new_password: ['', [Validators.required, Validators.minLength(8), passwordStrengthValidator(8)]],
        new_password2: ['', [Validators.required, newPasswordEqualsValidator()]],
    })

    username: string | null = null;

    constructor(
        private router: Router,
        private route: ActivatedRoute,
        private snackbar: MatSnackBar,
        private authService: AuthService,
        private userService: UserService
    ) { }

    ngOnInit(): void {
        this.username = this.route.snapshot.paramMap.get('username');
        if (this.username) {
            this.form.controls['old_password'].setValidators([]);
            this.form.controls['old_password'].updateValueAndValidity();
        }
    }

    onSubmit() {
        const formData = this.form.value;
        if (this.username) {
            if (formData.new_password)
                this.userService.changePassword(this.username, formData.new_password).subscribe({
                    complete: () => this.snackbar.open('Password changed successfully.', 'Close', { duration: 1500 })
                        .afterDismissed().subscribe(() => this.router.navigateByUrl("/users")),
                    error: (err) => this.snackbar.open(err.error.detail ?? err.message, 'Close')
                })

        } else {
            if (formData.old_password && formData.new_password)
                this.authService.changePassword(formData.old_password, formData.new_password).subscribe({
                    complete: () => this.snackbar.open('Password changed successfully.', 'Close', { duration: 1500 })
                        .afterDismissed().subscribe(() => this.router.navigateByUrl("/")),
                    error: (err) => this.snackbar.open(err.error.detail ?? err.message, 'Close')
                })
        }
    }
}
```

#### app/core/validators/index.ts

```typescript
export * from './password.validators';
```

#### app/core/validators/password.validators.ts

```typescript
import { AbstractControl, ValidationErrors, ValidatorFn } from '@angular/forms';

export function passwordStrengthValidator(minLength: number): ValidatorFn {
    return (control: AbstractControl): ValidationErrors | null => {
        const value: string = control.value;
        if (!value) {
            return null;
        }
        if (value.length < minLength)
            return { minlength: true }
        const hasUpperCase = /[A-Z]+/.test(value);
        const hasLowerCase = /[a-z]+/.test(value);
        const hasNumeric = /[0-9]+/.test(value);
        const passwordValid = hasUpperCase && hasLowerCase && hasNumeric;
        return !passwordValid ? { passwordStrength: true } : null;
    }
}

export function newPasswordEqualsValidator(): ValidatorFn {
    return (control: AbstractControl): ValidationErrors | null => {
        const value2: string = control.value;
        const value1: string = control.parent?.value.new_password
        return value1 != value2 ? { equals: true } : null;
    }
}
```

### Routes & Menu

`ChangePasswordComponent` has two modes. One is responsible for changing current user password and one for administrator to change
password for any user.

#### src/app/app.routes.ts

```typescript
    {
        path: 'change-password', title: "Personal AI Assistant - Change password", canActivate: [authGuard],
        loadComponent: () => import('./core/auth/change-password-form/change-password-form.component').then(m => m.ChangePasswordFormComponent)
    },
    {
        path: 'users/:username/change-password', title: "Personal AI Assistant - Change password", canActivate: [authGuard],
        loadComponent: () => import('./core/auth/change-password-form/change-password-form.component').then(m => m.ChangePasswordFormComponent)
    },
```

#### src/app/core/main-toolbar/main-toolbar.component.html

```html
        ...
        <button mat-menu-item routerLink="/change-password">
            <mat-icon>key</mat-icon>
            <span>Change password</span>
        </button>
        <button mat-menu-item (click)="authService.logout().subscribe()">
            <mat-icon>logout</mat-icon>
            <span>Sign out</span>
        </button>
    </mat-menu>
```

## 2.5 Password reset

### ResetPasswordRequestFormComponent

#### /src/app/core/auth/reset-password-request-form/reset-password-request-form.component.html

```html
<div class="centered-form">
    <form [formGroup]="form" (ngSubmit)="onSubmit()">
        <mat-card>
            <mat-card-header>
                <mat-card-title>Reset password request</mat-card-title>
            </mat-card-header>
            <mat-card-content>
                <mat-form-field class="full-width">
                    <mat-label>E-mail address</mat-label>
                    <input matInput type="email" placeholder="E-mail address" formControlName="email" required
                        autofocus>
                    @if (form.controls.email.hasError('required')) {
                    <mat-error>E-mail address is <strong>required</strong>.</mat-error>
                    }
                    @if (form.controls.email.hasError('email')) {
                    <mat-error>Input <strong>correct</strong> e-mail address.</mat-error>
                    }
                </mat-form-field>
                <p>If the user with the email address provided above is registered in the system, an email with a
                    password reset code will be sent to that address, which must be entered in the next form. </p>
            </mat-card-content>
            <mat-card-actions>
                <button mat-button type="button" routerLink="/login">Sign in</button>
                <button mat-raised-button color="primary" type="submit" [disabled]="!form.valid">Send request</button>
            </mat-card-actions>
        </mat-card>
    </form>
</div>
```

#### /src/app/core/auth/reset-password-request-form/reset-password-request-form.component.ts

```typescript
import { Component, inject } from '@angular/core';
import { FormBuilder, FormsModule, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSnackBar } from '@angular/material/snack-bar';
import { Router, RouterModule } from '@angular/router';
import { AuthService } from '../auth.service';
@Component({
    selector: 'app-reset-password-request-form',
    imports: [
        RouterModule,
        ReactiveFormsModule,
        FormsModule,
        MatCardModule,
        MatInputModule,
        MatButtonModule,
        MatFormFieldModule,
        MatCheckboxModule,
    ],
    templateUrl: './reset-password-request-form.component.html',
    styleUrl: './reset-password-request-form.component.scss'
})
export class ResetPasswordRequestFormComponent {

    private fb = inject(FormBuilder);

    form = this.fb.group({
        email: ['', [Validators.email, Validators.required]],
    });

    constructor(
        private router: Router,
        private snackbar: MatSnackBar,
        private authService: AuthService,
    ) { }

    onSubmit() {
        const email = this.form.value.email;
        if (email)
            this.authService.resetPasswordRequest(email).subscribe({
                complete: () => this.snackbar.open(`Code has been sent to ${email}`, "Reset password")
                    .afterDismissed().subscribe(() => this.router.navigateByUrl("/reset-password")),
                error: (err) => this.snackbar.open(err.error?.detail ?? err.message, "Close"),
            })
    }
}
```

#### /src/app/core/auth/reset-password-form/reset-password-form.component.html

```html
<div class="centered-form">
    <form (ngSubmit)="onSubmit()" [formGroup]="form">
        <mat-card>
            <mat-card-header>
                <mat-card-title>Reset password</mat-card-title>
            </mat-card-header>
            <mat-card-content>

                <mat-form-field class="full-width">
                    <mat-label>Email</mat-label>
                    <input type="email" matInput placeholder="Email" formControlName="email">
                    @if (form.controls.email.hasError('required')) {
                    <mat-error>Email is <strong>required</strong></mat-error>
                    }
                    @if (form.controls.email.hasError('email')) {
                    <mat-error>Please enter a <strong>valid</strong> email address</mat-error>
                    }
                </mat-form-field>

                <mat-form-field class="full-width">
                    <mat-label>Code received via email</mat-label>
                    <input matInput type="text" formControlName="reset_code" required>
                    @if (form.controls.reset_code.hasError('required')) {
                    <mat-error>Reset code is <strong>required</strong></mat-error>
                    }
                </mat-form-field>
                
                <mat-form-field class="full-width">
                    <mat-label>New password</mat-label>
                    <input matInput type="password" formControlName="new_password" required>
                    @if (form.controls.new_password.hasError('required')) {
                    <mat-error>Password is <strong>required</strong></mat-error>
                    }
                    @if (form.controls.new_password.hasError('passwordStrength')) {
                    <mat-error>Password must contain at least one <strong>lowercase letter, uppercase letter, and number</strong></mat-error>
                    }
                    @if (form.controls.new_password.hasError('minlength')) {
                    <mat-error>Password must be at least <strong>8 characters</strong> long</mat-error>
                    }
                </mat-form-field>
                
                <mat-form-field class="full-width">
                    <mat-label>Confirm new password</mat-label>
                    <input matInput type="password" formControlName="new_password2" required>
                    @if (form.controls.new_password2.hasError('required')) {
                    <mat-error>Password is <strong>required</strong></mat-error>
                    }
                    @if (form.controls.new_password2.hasError('equals')) {
                    <mat-error>Passwords do not <strong>match</strong></mat-error>
                    }
                </mat-form-field>

            </mat-card-content>
            <mat-card-actions>
                <button mat-button type="button" routerLink="/">Cancel</button>
                <button mat-raised-button color="primary" type="submit" [disabled]="!form.valid">Change</button>
            </mat-card-actions>
        </mat-card>
    </form>
</div>
```

#### /src/app/core/auth/reset-password-form/reset-password-form.component.ts

```typescript
import { Component, inject } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from "@angular/material/card";
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from "@angular/material/input";
import { MatSnackBar } from '@angular/material/snack-bar';
import { Router, RouterModule } from '@angular/router';
import { newPasswordEqualsValidator, passwordStrengthValidator } from '../../validators';
import { AuthService } from '../auth.service';

@Component({
    selector: 'app-reset-password-form',
    imports: [
        RouterModule,
        ReactiveFormsModule,
        MatCardModule,
        MatFormFieldModule,
        MatInputModule,
        MatButtonModule,
    ],
    templateUrl: './reset-password-form.component.html',
    styleUrl: './reset-password-form.component.scss'
})
export class ResetPasswordFormComponent {
    private fb = inject(FormBuilder);
    form = this.fb.group({
        email: ['', [Validators.email, Validators.required]],
        reset_code: ['', Validators.required],
        new_password: ['', [Validators.required, passwordStrengthValidator(8)]],
        new_password2: ['', [Validators.required, newPasswordEqualsValidator()]],
    })

    constructor(
        private router: Router,
        private snackbar: MatSnackBar,
        private authService: AuthService,
    ) { }

    onSubmit() {
        const formData = this.form.value;
        if (formData.email && formData.reset_code && formData.new_password)
            this.authService.resetPassword(formData.email, formData.reset_code, formData.new_password).subscribe({
                complete: () => this.snackbar.open('Password changed successfully', 'Sign in', { duration: 1500 })
                    .afterDismissed().subscribe(() => this.router.navigateByUrl("/login")),
                error: (err) => this.snackbar.open(err.error?.detail ?? err.message, 'Close')
            })
    }
}
```

#### src/app/app.routes.ts

```typescript
    {
        path: 'reset-password-request', title: "Personal AI Assistant - Reset password",
        loadComponent: () => import('./core/auth/reset-password-request-form/reset-password-request-form.component').then(mod => mod.ResetPasswordRequestFormComponent)
    },
    {
        path: 'reset-password', title: "Personal AI Assistant - Reset password",
        loadComponent: () => import('./core/auth/reset-password-form/reset-password-form.component').then(mod => mod.ResetPasswordFormComponent)
    },
```
