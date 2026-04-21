"""User and Session data access.

Repositories own SQL. Services own orchestration. Keep SQLAlchemy out of
everything except this layer.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_refresh_token
from app.models.user import Session, User


class UserRepo:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        return await self.db.get(User, user_id)

    async def get_by_email(self, email: str) -> User | None:
        stmt = select(User).where(User.email == email.lower())
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def create(
        self,
        *,
        email: str,
        password_hash: str,
        display_name: str | None,
        locale: str,
    ) -> User:
        user = User(
            email=email.lower(),
            password_hash=password_hash,
            display_name=display_name,
            locale=locale,
        )
        self.db.add(user)
        await self.db.flush()
        await self.db.refresh(user)
        return user

    async def touch_last_login(self, user_id: uuid.UUID) -> None:
        stmt = (
            update(User)
            .where(User.id == user_id)
            .values(last_login_at=datetime.utcnow())
        )
        await self.db.execute(stmt)

    async def update_password_hash(self, user_id: uuid.UUID, new_hash: str) -> None:
        stmt = update(User).where(User.id == user_id).values(password_hash=new_hash)
        await self.db.execute(stmt)


class SessionRepo:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def create(
        self,
        *,
        user_id: uuid.UUID,
        refresh_token_hash: str,
        expires_at: datetime,
        user_agent: str | None,
        ip_address: str | None,
    ) -> Session:
        sess = Session(
            user_id=user_id,
            refresh_token_hash=refresh_token_hash,
            expires_at=expires_at,
            user_agent=(user_agent or "")[:500] or None,
            ip_address=ip_address,
        )
        self.db.add(sess)
        await self.db.flush()
        return sess

    async def get_active_by_raw_token(self, raw_token: str) -> Session | None:
        h = hash_refresh_token(raw_token)
        stmt = select(Session).where(Session.refresh_token_hash == h)
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def revoke(self, session_id: uuid.UUID) -> None:
        stmt = (
            update(Session)
            .where(Session.id == session_id, Session.revoked_at.is_(None))
            .values(revoked_at=datetime.utcnow())
        )
        await self.db.execute(stmt)

    async def revoke_all_for_user(self, user_id: uuid.UUID) -> None:
        """Used on suspected token theft — nukes every active session."""
        stmt = (
            update(Session)
            .where(Session.user_id == user_id, Session.revoked_at.is_(None))
            .values(revoked_at=datetime.utcnow())
        )
        await self.db.execute(stmt)
