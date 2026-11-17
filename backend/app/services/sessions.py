"""Rotating refresh tokens. The hash is what the database stores."""

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.refresh_token import RefreshToken


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def issue_refresh_token(db: AsyncSession, user_id: uuid.UUID, family_id: uuid.UUID | None = None) -> str:
    raw = secrets.token_urlsafe(32)
    db.add(
        RefreshToken(
            user_id=user_id,
            token_hash=_hash(raw),
            family_id=family_id or uuid.uuid4(),
            expires_at=_now() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        )
    )
    await db.flush()
    return raw


async def _revoke_family(db: AsyncSession, family_id: uuid.UUID) -> None:
    await db.execute(
        update(RefreshToken)
        .where(RefreshToken.family_id == family_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=_now())
    )


async def rotate_refresh_token(db: AsyncSession, raw: str) -> RefreshToken:
    row = await db.scalar(select(RefreshToken).where(RefreshToken.token_hash == _hash(raw)))
    if row is None or row.expires_at <= _now():
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sign in again.")
    if row.revoked_at is not None:
        await _revoke_family(db, row.family_id)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sign in again.")
    row.revoked_at = _now()
    await db.flush()
    return row


async def revoke_refresh_token(db: AsyncSession, raw: str) -> None:
    row = await db.scalar(select(RefreshToken).where(RefreshToken.token_hash == _hash(raw)))
    if row is None:
        return
    await _revoke_family(db, row.family_id)
