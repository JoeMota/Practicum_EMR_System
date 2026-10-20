import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.clinical import Course, CourseMembership
from app.models.user import User

ROLE_PERMISSIONS: dict[str, list[str]] = {
    "student": ["encounter:advance", "note:author", "referral:create"],
    "instructor": [
        "patient:create",
        "patient:update_status",
        "patient:reset_practice",
        "encounter:advance",
        "note:cosign",
        "referral:create",
        "roster:import",
        "instructor:remove",
        "audit:view",
    ],
    "admin": [
        "patient:create",
        "patient:update_status",
        "patient:reset_practice",
        "roster:import",
        "audit:view",
        "instructor:remove",
        "course:create",
        "course:manage_status",
        "course:manage_access",
        "user:manage_access",
        "report:run",
    ],
    "front_desk": ["patient:create"],
    "patient": [],
}

CLINICAL_ROLES = set(ROLE_PERMISSIONS)


def can(role: str, permission: str) -> bool:
    return permission in ROLE_PERMISSIONS.get(role, [])


def require(role: str, permission: str, message: str) -> None:
    if role not in CLINICAL_ROLES:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Unknown role.")
    if not can(role, permission):
        raise HTTPException(status.HTTP_403_FORBIDDEN, message)


async def memberships_for(db: AsyncSession, user_id: uuid.UUID) -> list[CourseMembership]:
    result = await db.scalars(
        select(CourseMembership)
        .join(Course, Course.id == CourseMembership.course_id)
        .where(CourseMembership.user_id == user_id)
        .where(Course.status != "archived")
        .options(
            selectinload(CourseMembership.role),
            selectinload(CourseMembership.discipline),
            selectinload(CourseMembership.course),
        )
    )
    return list(result.all())


async def ensure_course_open(db: AsyncSession, course_id: uuid.UUID) -> Course:
    course = await db.get(Course, course_id)
    if course is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Course not found.")
    if course.status in {"ended", "archived"}:
        detail = "This course has ended and cannot be edited." if course.status == "ended" else "This course has been archived and cannot be edited."
        raise HTTPException(status.HTTP_409_CONFLICT, detail)
    return course


def holds_role(user: User, role: str, rows: list[CourseMembership]) -> bool:
    if role == "admin" and any(item.code == "admin" for item in user.roles):
        return True
    return any(row.role.code == role for row in rows)


def require_held_role(user: User, role: str, rows: list[CourseMembership]) -> None:
    if not holds_role(user, role, rows):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You don't have that role.")


def require_course(role: str, course_id: uuid.UUID, user: User, rows: list[CourseMembership]) -> None:
    require_held_role(user, role, rows)
    if role == "admin" and any(item.code == "admin" for item in user.roles):
        return
    if not any(row.role.code == role and row.course_id == course_id for row in rows):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You are not in this course.")


def full_name(user: User) -> str:
    return f"{user.first_name} {user.last_name}"
