import re
import secrets
import uuid
from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException, Query, Request, status
from sqlalchemy import func, select

from app.api.deps import CurrentUser, DbSession
from app.core.security import hash_password
from app.models.clinical import Course, CourseMembership
from app.models.user import Discipline, Role, User
from app.schemas.clinical import (
    CourseCreate,
    CourseOut,
    CourseStatusPatch,
    PublicUser,
    RosterImport,
    RosterImportResult,
    TempPassword,
)
from app.services.access import ensure_course_open, memberships_for, require, require_course, require_held_role
from app.services.audit import log_event
from app.services.serialize import course_out, user_out

router = APIRouter(prefix="/courses", tags=["courses"])
UTEP_EMAIL = re.compile(r"@(miners\.)?utep\.edu$", re.IGNORECASE)
COURSE_TRANSITIONS = {
    "planned": {"active"},
    "active": {"ended"},
    "ended": {"active", "archived"},
    "archived": set(),
}


def _ip(request: Request) -> str | None:
    return request.client.host if request.client else None


def _require_admin(user: User, rows) -> None:
    require_held_role(user, "admin", rows)


@router.post("", response_model=CourseOut, response_model_exclude_none=True, status_code=status.HTTP_201_CREATED)
async def create_course(body: CourseCreate, db: DbSession, user: CurrentUser, request: Request):
    rows = await memberships_for(db, user.id)
    _require_admin(user, rows)
    require("admin", "course:create", "Your role can't create courses.")
    code = body.code.strip()
    title = body.title.strip()
    term = body.term.strip()
    if not code or not title or not term:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Course code, title, and term are required.")
    if await db.scalar(select(Course.id).where(Course.code == code, Course.term == term)):
        raise HTTPException(status.HTTP_409_CONFLICT, "A course with that code already exists for that term.")
    course = Course(code=code, title=title, term=term, status="planned")
    db.add(course)
    await db.flush()
    await log_event(
        db,
        action="course.create",
        entity_type="course",
        entity_id=str(course.id),
        actor_user_id=user.id,
        course_id=course.id,
        ip_address=_ip(request),
        detail=f"{course.code}: {course.title}",
    )
    await db.commit()
    return course_out(course, [])


async def _instructors(db, course_id: uuid.UUID) -> list[User]:
    rows = (
        await db.scalars(
            select(CourseMembership).where(CourseMembership.course_id == course_id)
        )
    ).all()
    found: list[User] = []
    seen: set[uuid.UUID] = set()
    for row in rows:
        role = await db.get(Role, row.role_id)
        if role and role.code == "instructor" and row.user_id not in seen:
            user = await db.get(User, row.user_id)
            if user:
                found.append(user)
                seen.add(user.id)
    return found


@router.get("", response_model=list[CourseOut], response_model_exclude_none=True)
async def list_courses(db: DbSession, user: CurrentUser):
    rows = await memberships_for(db, user.id)
    ids = {row.course_id for row in rows}
    if any(item.code == "admin" for item in user.roles):
        ids.update(await db.scalars(select(Course.id)))
    courses = list((await db.scalars(select(Course).where(Course.id.in_(ids)).order_by(Course.code))).all()) if ids else []
    payload = []
    for course in courses:
        instructors = await _instructors(db, course.id)
        payload.append(course_out(course, [str(person.id) for person in instructors]))
    return payload


@router.get("/{course_id}", response_model=CourseOut, response_model_exclude_none=True)
async def get_course(course_id: uuid.UUID, db: DbSession, user: CurrentUser):
    course = await db.get(Course, course_id)
    if course is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Course not found.")
    rows = await memberships_for(db, user.id)
    if course.id not in {row.course_id for row in rows} and not any(item.code == "admin" for item in user.roles):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You are not in this course.")
    instructors = await _instructors(db, course.id)
    return course_out(course, [str(person.id) for person in instructors])


@router.get("/{course_id}/instructors", response_model=list[PublicUser], response_model_exclude_none=True)
async def list_instructors(course_id: uuid.UUID, db: DbSession, user: CurrentUser):
    await get_course(course_id, db, user)
    return [await user_out(db, person) for person in await _instructors(db, course_id)]


@router.get("/{course_id}/roster", response_model=list[PublicUser], response_model_exclude_none=True)
async def list_roster(course_id: uuid.UUID, db: DbSession, user: CurrentUser, request: Request):
    rows = await memberships_for(db, user.id)
    role = _staff_role(user, rows, course_id)
    require(role, "roster:import", "Your role can't view the roster.")
    members = (
        await db.scalars(select(CourseMembership).where(CourseMembership.course_id == course_id))
    ).all()
    students: list[User] = []
    seen: set[uuid.UUID] = set()
    for member in members:
        held = await db.get(Role, member.role_id)
        if held and held.code == "student" and member.user_id not in seen:
            person = await db.get(User, member.user_id)
            if person:
                students.append(person)
                seen.add(person.id)
    return [await user_out(db, person) for person in students]


@router.post("/{course_id}/roster/import", response_model=RosterImportResult)
async def import_roster(
    course_id: uuid.UUID, body: RosterImport, db: DbSession, user: CurrentUser, request: Request
):
    rows = await memberships_for(db, user.id)
    role = _staff_role(user, rows, course_id)
    require(role, "roster:import", "Your role can't import a roster.")
    if body.role == "instructor":
        require(role, "course:manage_access", "Only admins can add instructors.")
    if any(row.problem for row in body.rows):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Fix the flagged rows before importing.")
    course = await db.get(Course, course_id)
    if course is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Course not found.")
    await ensure_course_open(db, course_id)
    member_role = await db.scalar(select(Role).where(Role.code == body.role))
    discipline = await db.scalar(select(Discipline).where(Discipline.code == body.discipline))
    if member_role is None or discipline is None:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Roles are not seeded.")
    added = 0
    already = 0
    passwords: list[TempPassword] = []
    for row in body.rows:
        email = row.email.strip().lower()
        if not UTEP_EMAIL.search(email):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"{email} is not a UTEP email address.")
        person = await db.scalar(select(User).where(User.email == email))
        if person is None:
            first, last = _split_name(row.full_name)
            temporary = secrets.token_urlsafe(9)
            person = User(
                email=email,
                first_name=first,
                last_name=last,
                university_id=row.university_id,
                hashed_password=hash_password(temporary),
                must_change_password=True,
                is_active=True,
            )
            db.add(person)
            await db.flush()
            passwords.append(TempPassword(email=email, password=temporary))
        existing = await db.scalar(
            select(CourseMembership).where(
                CourseMembership.user_id == person.id,
                CourseMembership.course_id == course_id,
                CourseMembership.role_id == member_role.id,
            )
        )
        if existing:
            already += 1
            continue
        db.add(
            CourseMembership(
                user_id=person.id,
                course_id=course_id,
                role_id=member_role.id,
                discipline_id=discipline.id,
            )
        )
        added += 1
    await log_event(
        db,
        action="roster.import",
        entity_type="course",
        entity_id=str(course_id),
        actor_user_id=user.id,
        course_id=course_id,
        ip_address=_ip(request),
        detail=f"{added} {body.role}s added, {already} already enrolled",
    )
    await db.commit()
    return RosterImportResult(added=added, already_enrolled=already, temporary_passwords=passwords)


@router.delete("/{course_id}/roster/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_from_course(
    course_id: uuid.UUID,
    user_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
    request: Request,
    role: Annotated[Literal["student", "instructor"], Query()] = "student",
):
    rows = await memberships_for(db, user.id)
    staff_role = _staff_role(user, rows, course_id)
    require(staff_role, "roster:import", "Your role can't edit the roster.")
    if role == "instructor":
        require(staff_role, "instructor:remove", "Your role can't remove instructors.")
        if user_id == user.id:
            raise HTTPException(status.HTTP_409_CONFLICT, "You can't remove yourself from the course.")
    target_role = await db.scalar(select(Role).where(Role.code == role))
    if target_role is None:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Roles are not seeded.")
    membership = await db.scalar(
        select(CourseMembership).where(
            CourseMembership.user_id == user_id,
            CourseMembership.course_id == course_id,
            CourseMembership.role_id == target_role.id,
        )
    )
    if membership and role == "instructor":
        instructor_count = await db.scalar(
            select(func.count())
            .select_from(CourseMembership)
            .join(Role, Role.id == CourseMembership.role_id)
            .where(CourseMembership.course_id == course_id, Role.code == "instructor")
        )
        if instructor_count <= 1:
            raise HTTPException(status.HTTP_409_CONFLICT, "A course must have at least one instructor.")
    if membership:
        await db.delete(membership)
    await log_event(
        db,
        action="roster.remove",
        entity_type="course",
        entity_id=str(course_id),
        actor_user_id=user.id,
        course_id=course_id,
        ip_address=_ip(request),
        detail=f"{role} user/{user_id}",
    )
    await db.commit()


@router.post("/{course_id}/status", response_model=CourseOut, response_model_exclude_none=True)
async def update_course_status(
    course_id: uuid.UUID, body: CourseStatusPatch, db: DbSession, user: CurrentUser, request: Request
):
    rows = await memberships_for(db, user.id)
    _require_admin(user, rows)
    require("admin", "course:manage_status", "Your role can't manage course status.")
    course = await db.get(Course, course_id)
    if course is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Course not found.")
    if body.status not in COURSE_TRANSITIONS[course.status]:
        raise HTTPException(status.HTTP_409_CONFLICT, f"Cannot change a {course.status} course to {body.status}.")
    previous = course.status
    course.status = body.status
    await log_event(
        db,
        action="course.status",
        entity_type="course",
        entity_id=str(course.id),
        actor_user_id=user.id,
        course_id=course.id,
        ip_address=_ip(request),
        detail=f"{previous} -> {course.status}",
    )
    await db.commit()
    return course_out(course, [str(person.id) for person in await _instructors(db, course.id)])


def _staff_role(user: User, rows, course_id: uuid.UUID) -> str:
    if any(row.role.code == "instructor" and row.course_id == course_id for row in rows):
        require_course("instructor", course_id, user, rows)
        return "instructor"
    if any(item.code == "admin" for item in user.roles):
        return "admin"
    raise HTTPException(status.HTTP_403_FORBIDDEN, "Your role can't view the roster.")


def _split_name(full_name: str) -> tuple[str, str]:
    cleaned = " ".join(full_name.split())
    if " " not in cleaned:
        return cleaned, cleaned
    first, last = cleaned.rsplit(" ", 1)
    return first, last
