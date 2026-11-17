import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import DUMMY_HASH, verify_password
from app.models.user import Role, User


def _user_with_access():
    # Async can't lazy-load, so roles -> permissions and discipline are loaded up front.
    return select(User).options(
        selectinload(User.roles).selectinload(Role.permissions),
        selectinload(User.discipline),
    )


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(_user_with_access().where(User.email == email.strip().lower()))
    return result.scalar_one_or_none()


async def get_user_by_id(db: AsyncSession, user_id: uuid.UUID) -> User | None:
    result = await db.execute(_user_with_access().where(User.id == user_id))
    return result.scalar_one_or_none()


def is_usable(user: User) -> bool:
    return user.is_active and user.deleted_at is None and user.archived_at is None and user.purged_at is None


async def authenticate_user(db: AsyncSession, email: str, password: str) -> User | None:
    user = await get_user_by_email(db, email)
    if user is None:
        verify_password(password, DUMMY_HASH)  # equalize timing
        return None
    if not verify_password(password, user.hashed_password) or not is_usable(user):
        return None
    return user


def permission_codes(user: User) -> set[str]:
    return {perm.code for role in user.roles for perm in role.permissions}
