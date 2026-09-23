import uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession
from app.models.course import Course, Enrollment
from app.models.user import User
from app.schemas.clinical import CourseOut, SessionUserOut
from app.services.access import list_enrollments
from app.services.serializers import course_out, session_user_from

router = APIRouter(prefix="/courses", tags=["courses"])


@router.get("", response_model=list[CourseOut])
async def list_my_courses(user: CurrentUser, db: DbSession):
    enrollments = await list_enrollments(db, user.id)
    course_ids = {e.course_id for e in enrollments}
    if not course_ids:
        return []
    courses = (await db.scalars(select(Course).where(Course.id.in_(course_ids), Course.deleted_at.is_(None)))).all()
    return [await _course_with_instructors(db, c) for c in courses]


@router.get("/{course_id}", response_model=CourseOut)
async def get_course(course_id: uuid.UUID, user: CurrentUser, db: DbSession):
    course = await db.get(Course, course_id)
    if course is None or course.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")
    return await _course_with_instructors(db, course)


@router.get("/{course_id}/instructors", response_model=list[SessionUserOut])
async def list_instructors(course_id: uuid.UUID, user: CurrentUser, db: DbSession):
    rows = (
        await db.execute(
            select(Enrollment).where(
                Enrollment.course_id == course_id,
                Enrollment.app_role == "instructor",
            )
        )
    ).scalars().all()
    users: list[SessionUserOut] = []
    for e in rows:
        u = await db.get(User, e.user_id)
        if u is None or not u.is_active:
            continue
        enrollments = await list_enrollments(db, u.id)
        users.append(session_user_from(u, enrollments))
    return users


async def _course_with_instructors(db: DbSession, course: Course) -> CourseOut:
    instructor_ids = (
        await db.execute(
            select(Enrollment.user_id).where(
                Enrollment.course_id == course.id,
                Enrollment.app_role == "instructor",
            )
        )
    ).scalars().all()
    return course_out(course, list(instructor_ids))
