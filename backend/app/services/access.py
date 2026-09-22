"""Enrollment helpers and app-role checks used across clinical routes."""
from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.course import Enrollment
from app.models.user import User
from app.services.auth import permission_codes


async def list_enrollments(db: AsyncSession, user_id: uuid.UUID) -> list[Enrollment]:
    result = await db.execute(select(Enrollment).where(Enrollment.user_id == user_id))
    return list(result.scalars().all())


async def enrollments_for_course(db: AsyncSession, course_id: uuid.UUID) -> list[Enrollment]:
    result = await db.execute(select(Enrollment).where(Enrollment.course_id == course_id))
    return list(result.scalars().all())


def has_app_role(enrollments: list[Enrollment], role: str, course_id: uuid.UUID | None = None) -> bool:
    for e in enrollments:
        if e.app_role != role:
            continue
        if course_id is None or e.course_id == course_id:
            return True
    return False


def is_staff(enrollments: list[Enrollment], course_id: uuid.UUID | None = None) -> bool:
    return any(
        has_app_role(enrollments, r, course_id)
        for r in ("instructor", "admin", "front_desk")
    )


def can_cosign(user: User) -> bool:
    return "note:cosign" in permission_codes(user)


def can_manage_roster(user: User) -> bool:
    return "user:manage" in permission_codes(user)


def can_reset_practice(user: User) -> bool:
    return "simulation:manage" in permission_codes(user)


def can_read_audit(user: User) -> bool:
    return "audit:read" in permission_codes(user)


async def load_user_with_enrollments(db: AsyncSession, user_id: uuid.UUID) -> tuple[User | None, list[Enrollment]]:
    from app.services.auth import get_user_by_id

    user = await get_user_by_id(db, user_id)
    if user is None:
        return None, []
    return user, await list_enrollments(db, user_id)


async def get_users_by_ids(db: AsyncSession, ids: list[uuid.UUID]) -> dict[uuid.UUID, User]:
    if not ids:
        return {}
    from app.models.user import Role

    result = await db.execute(
        select(User)
        .options(selectinload(User.roles).selectinload(Role.permissions), selectinload(User.discipline))
        .where(User.id.in_(ids))
    )
    return {u.id: u for u in result.scalars().all()}
