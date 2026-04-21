"""Auth orchestration: register, login, refresh, logout.

Rules encoded here:
- Refresh tokens are single-use. Each refresh issues a new one and revokes the old.
- Reusing a revoked refresh token → we assume theft and revoke ALL sessions for
  that user. They'll have to log in again everywhere.
- Passwords are re-hashed on login if the stored hash uses older argon2 params.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.errors import ConflictError, UnauthorizedError
from app.core.logging import get_logger
from app.core.security import (
    create_access_token,
    generate_refresh_token,
    hash_password,
    password_needs_rehash,
    refresh_token_expiry,
    verify_password,
)
from app.models.user import Session as UserSession
from app.models.user import User
from app.repos.user_repo import SessionRepo, UserRepo
from app.schemas.auth import TokenPair

log = get_logger(__name__)


class AuthService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.users = UserRepo(db)
        self.sessions = SessionRepo(db)

    # ---------------- register ----------------

    async def register(
        self,
        *,
        email: str,
        password: str,
        display_name: str | None,
        locale: str,
        user_agent: str | None,
        ip_address: str | None,
    ) -> tuple[User, TokenPair]:
        if await self.users.get_by_email(email):
            raise ConflictError("An account with that email already exists.")

        user = await self.users.create(
            email=email,
            password_hash=hash_password(password),
            display_name=display_name,
            locale=locale,
        )
        log.info("user_registered", user_id=str(user.id), email=user.email)

        tokens = await self._issue_tokens(user, user_agent, ip_address)
        return user, tokens

    # ---------------- login ----------------

    async def login(
        self,
        *,
        email: str,
        password: str,
        user_agent: str | None,
        ip_address: str | None,
    ) -> tuple[User, TokenPair]:
        user = await self.users.get_by_email(email)

        # Constant-ish time: always do one hash verify even on miss, to avoid
        # leaking "email exists" via timing.
        if user is None:
            _ = verify_password(password, "$argon2id$v=19$m=19456,t=2,p=1$AAAAAAAAAAAAAAAAAAAAAA$AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA")  # noqa: E501
            raise UnauthorizedError("Invalid email or password.")

        if not verify_password(password, user.password_hash):
            raise UnauthorizedError("Invalid email or password.")

        if not user.is_active:
            raise UnauthorizedError("Account is disabled.")

        # Opportunistic rehash if params are outdated
        if password_needs_rehash(user.password_hash):
            await self.users.update_password_hash(user.id, hash_password(password))

        await self.users.touch_last_login(user.id)
        log.info("user_login", user_id=str(user.id))

        tokens = await self._issue_tokens(user, user_agent, ip_address)
        return user, tokens

    # ---------------- refresh ----------------

    async def refresh(
        self,
        *,
        raw_refresh_token: str,
        user_agent: str | None,
        ip_address: str | None,
    ) -> tuple[User, TokenPair]:
        sess = await self.sessions.get_active_by_raw_token(raw_refresh_token)
        if sess is None:
            raise UnauthorizedError("Invalid refresh token.")

        now = datetime.now(UTC)

        # Reuse of a revoked token → assume theft, nuke all sessions for that user.
        if sess.revoked_at is not None:
            log.warning(
                "refresh_token_reuse_detected",
                user_id=str(sess.user_id),
                session_id=str(sess.id),
            )
            await self.sessions.revoke_all_for_user(sess.user_id)
            raise UnauthorizedError("Refresh token has been revoked.")

        # Check for naturally-expired session (we compare UTC aware)
        if sess.expires_at.replace(tzinfo=UTC) <= now:
            await self.sessions.revoke(sess.id)
            raise UnauthorizedError("Refresh token has expired.")

        user = await self.users.get_by_id(sess.user_id)
        if user is None or not user.is_active:
            await self.sessions.revoke(sess.id)
            raise UnauthorizedError("User not found or inactive.")

        # Rotate: revoke this session, issue a new one.
        await self.sessions.revoke(sess.id)
        tokens = await self._issue_tokens(user, user_agent, ip_address)
        log.info("token_refreshed", user_id=str(user.id))
        return user, tokens

    # ---------------- logout ----------------

    async def logout(self, *, raw_refresh_token: str) -> None:
        sess = await self.sessions.get_active_by_raw_token(raw_refresh_token)
        if sess is not None and sess.revoked_at is None:
            await self.sessions.revoke(sess.id)
            log.info("user_logout", user_id=str(sess.user_id))

    # ---------------- helpers ----------------

    async def _issue_tokens(
        self,
        user: User,
        user_agent: str | None,
        ip_address: str | None,
    ) -> TokenPair:
        access = create_access_token(user.id, extra_claims={"role": user.role})
        raw_refresh, hashed = generate_refresh_token()
        await self.sessions.create(
            user_id=user.id,
            refresh_token_hash=hashed,
            expires_at=refresh_token_expiry(),
            user_agent=user_agent,
            ip_address=ip_address,
        )
        return TokenPair(
            access_token=access,
            refresh_token=raw_refresh,
            expires_in=settings.jwt_access_ttl_minutes * 60,
        )
