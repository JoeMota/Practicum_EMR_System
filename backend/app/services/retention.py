"""Archived accounts stay for two years, then the login is anonymized. Charts and notes stay."""

import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.clinical import CourseMembership, PatientIntake
from app.models.user import User
from app.services.charts import utcnow

RETENTION = timedelta(days=365 * 2)


def retention_ends(archived_at: datetime) -> datetime:
    value = archived_at if archived_at.tzinfo else archived_at.replace(tzinfo=timezone.utc)
    return value + RETENTION


async def anonymize_user(db: AsyncSession, user: User) -> None:
    await db.execute(delete(CourseMembership).where(CourseMembership.user_id == user.id))
    await db.execute(delete(PatientIntake).where(PatientIntake.updated_by_user_id == user.id))
    user.first_name = "Archived"
    user.last_name = "Student"
    user.email = f"archived-{user.id}@invalid.local"
    user.university_id = None
    user.phone_last4 = None
    user.hashed_password = hash_password(secrets.token_urlsafe(18))
    user.is_active = False
    user.must_change_password = False
    user.purged_at = utcnow()


async def purge_expired(db: AsyncSession) -> int:
    cutoff = utcnow() - RETENTION
    users = list(
        (
            await db.scalars(
                select(User).where(User.archived_at.is_not(None), User.archived_at <= cutoff, User.purged_at.is_(None))
            )
        ).all()
    )
    for user in users:
        await anonymize_user(db, user)
    return len(users)
