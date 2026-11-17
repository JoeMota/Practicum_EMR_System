import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.clinical import Course, CourseMembership
from app.models.user import User

TEACHING_PERMISSIONS = [
    "patient:create",
    "patient:update_status",
    "patient:reset_practice",
    "encounter:advance",
    "note:cosign",
    "note:view_sensitive",
    "referral:create",
    "audit:view",
    "case:author",
    "report:export_teaching",
]

ROLE_PERMISSIONS: dict[str, list[str]] = {
    "student": ["encounter:advance", "note:author", "referral:create"],
    "instructor": list(TEACHING_PERMISSIONS),
    "course_coordinator": [*TEACHING_PERMISSIONS, "instructor:manage"],
    "admin": [
        "roster:import",
        "audit:view",
        "instructor:manage",
        "instructor:remove",
        "course:create",
        "course:manage_status",
        "course:manage_access",
        "user:manage_access",
        "report:run",
        "report:export_teaching",
        "note:view_sensitive",
    ],
    "front_desk": [],
    "patient": ["portal:view", "portal:edit"],
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
        .where(CourseMembership.deactivated_at.is_(None))
        .where(Course.status != "archived")
        .options(
            selectinload(CourseMembership.role),
            selectinload(CourseMembership.discipline),
            selectinload(CourseMembership.course),
        )
    )
    return list(result.all())


async def ensure_student_may_enter(db: AsyncSession, role: str, course_id: uuid.UUID) -> None:
    if role != "student":
        return
    course = await db.get(Course, course_id)
    if course is not None and course.status == "ended":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "This course has ended.")


async def ensure_course_open(db: AsyncSession, course_id: uuid.UUID) -> Course:
    course = await db.get(Course, course_id)
    if course is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Course not found.")
    if course.status in {"ended", "archived"}:
        detail = "This course has ended and cannot be edited." if course.status == "ended" else "This course has been archived and cannot be edited."
        raise HTTPException(status.HTTP_409_CONFLICT, detail)
    return course


def holds_role(user: User, role: str, rows: list[CourseMembership]) -> bool:
    if role in {"admin", "patient"} and any(item.code == role for item in user.roles):
        return True
    return any(row.role.code == role for row in rows)


def require_acting_role(user: User, role: str) -> None:
    """ADM-05: authorize against the session's active role only."""
    if user.acting_role and user.acting_role != role:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            f"You're signed in as {user.acting_role}. Switch roles to use {role} permissions.",
        )


def require_held_role(user: User, role: str, rows: list[CourseMembership]) -> None:
    require_acting_role(user, role)
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


def may_read_note(role: str, memberships: list[CourseMembership], course_id: uuid.UUID, note) -> bool:
    """Protected and psychiatry notes stay with the same discipline, or with an admin.

    A teaching seat with no discipline still covers the course. That keeps instructors
    who are not pinned to one profession able to open a protected note.
    """
    kind = getattr(note, "sensitivity", None) or "standard"
    protected = kind in {"psychiatry", "protected"} or bool(getattr(note, "sensitive", False))
    if not protected:
        return True
    if role == "admin":
        return True
    if not can(role, "note:view_sensitive"):
        return False
    discipline = note.discipline.code if getattr(note, "discipline", None) is not None else None
    for row in memberships:
        if row.course_id != course_id or row.role.code != role:
            continue
        if row.discipline is None or (discipline is not None and row.discipline.code == discipline):
            return True
    return False
