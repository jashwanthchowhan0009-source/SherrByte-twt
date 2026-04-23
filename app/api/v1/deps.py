"""FastAPI dependencies — the glue between requests and services.

Every route that needs a DB session takes `db: AsyncSession = Depends(get_session)`.
Every protected route takes `user: User = Depends(get_current_user)`.
"""

from __future__ import annotations

import uuid
from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from slowapi import Limiter
from slowapi.util import get_remote_address
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import UnauthorizedError
from app.core.security import decode_access_token
from app.db.session import SessionLocal
from app.models.user import User
from app.repos.user_repo import UserRepo


# ---------------- DB session ----------------


async def get_session() -> AsyncIterator[AsyncSession]:
    """One session per request. Commits on clean exit, rolls back on exception."""
    async with SessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


DB = Annotated[AsyncSession, Depends(get_session)]


# ---------------- Auth ----------------

# auto_error=False → we raise our own UnauthorizedError instead of FastAPI's 403
_bearer = HTTPBearer(auto_error=False, description="Paste access_token here.")


async def get_current_user(
    request: Request,
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    db: DB,
) -> User:
    if creds is None or not creds.credentials:
        raise UnauthorizedError("Missing Authorization header.")

    payload = decode_access_token(creds.credentials)
    try:
        user_id = uuid.UUID(payload["sub"])
    except (KeyError, ValueError) as e:
        raise UnauthorizedError("Malformed token.") from e

    user = await UserRepo(db).get_by_id(user_id)
    if user is None or not user.is_active:
        raise UnauthorizedError("User not found or inactive.")

    # Make user_id available to logs for the rest of the request
    from app.core.logging import user_id_ctx
    user_id_ctx.set(str(user.id))

    # Stash on request.state so routes that want the raw User don't re-look-up
    request.state.user = user
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


# ---------------- Rate limiter ----------------


def _rate_key(request: Request) -> str:
    """Rate-limit by user id when authenticated, else by IP."""
    user = getattr(request.state, "user", None)
    if user is not None:
        return f"user:{user.id}"
    return f"ip:{get_remote_address(request)}"


limiter = Limiter(key_func=_rate_key, default_limits=[])
