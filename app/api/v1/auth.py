"""Auth HTTP routes.

All routes are thin — they parse the request, call the service, and return the
response. No SQL, no business rules here.
"""

from __future__ import annotations

from fastapi import APIRouter, Request, Response, status

from app.deps import DB, CurrentUser, limiter
from app.schemas.auth import (
    AuthResponse,
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    RegisterRequest,
    TokenPair,
    UserOut,
)
from app.services.auth_service import AuthService

router = APIRouter()


def _client_ip(request: Request) -> str | None:
    """Trust Fly.io's X-Forwarded-For; fall back to the direct peer."""
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else None


def _user_agent(request: Request) -> str | None:
    return request.headers.get("user-agent")


@router.post(
    "/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new account",
)
@limiter.limit("10/hour")
async def register(request: Request, payload: RegisterRequest, db: DB) -> AuthResponse:
    user, tokens = await AuthService(db).register(
        email=payload.email,
        password=payload.password,
        display_name=payload.display_name,
        locale=payload.locale,
        user_agent=_user_agent(request),
        ip_address=_client_ip(request),
    )
    return AuthResponse(user=UserOut.model_validate(user), tokens=tokens)


@router.post(
    "/login",
    response_model=AuthResponse,
    summary="Log in with email + password",
)
@limiter.limit("20/minute")
async def login(request: Request, payload: LoginRequest, db: DB) -> AuthResponse:
    user, tokens = await AuthService(db).login(
        email=payload.email,
        password=payload.password,
        user_agent=_user_agent(request),
        ip_address=_client_ip(request),
    )
    return AuthResponse(user=UserOut.model_validate(user), tokens=tokens)


@router.post(
    "/refresh",
    response_model=TokenPair,
    summary="Rotate a refresh token for a new access+refresh pair",
)
@limiter.limit("60/minute")
async def refresh(request: Request, payload: RefreshRequest, db: DB) -> TokenPair:
    _user, tokens = await AuthService(db).refresh(
        raw_refresh_token=payload.refresh_token,
        user_agent=_user_agent(request),
        ip_address=_client_ip(request),
    )
    return tokens


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke the given refresh token",
)
async def logout(payload: LogoutRequest, db: DB) -> Response:
    """Fixes the AssertionError by returning a proper No Content response."""
    await AuthService(db).logout(raw_refresh_token=payload.refresh_token)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/me", response_model=UserOut, summary="Current authenticated user")
async def me(user: CurrentUser) -> UserOut:
    return UserOut.model_validate(user)
