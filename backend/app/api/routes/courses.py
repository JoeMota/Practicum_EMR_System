import re
import secrets
import uuid
from datetime import datetime, timezone
from typing import Annotated, Literal

from fastapi import APIRouter, File, HTTPException, Query, Request, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser, DbSession
from app.core.security import hash_password
from app.models.clinical import Course, CourseMembership
from app.models.user import Discipline, Role, User
from app.schemas.clinical import (
    CourseCreate,
    CourseOut,
    CoursePolicyPatch,
    CourseStatusPatch,
    InactivityDaysPatch,
    EnrollmentCreate,
    PublicUser,
    RosterImport,
    RosterImportResult,
    TempPassword,
)
from app.services.access import can, ensure_course_open, memberships_for, require, require_course, require_held_role
from app.services.audit import log_event
from app.services.rubric_import import guide_from_upload
from app.services.serialize import course_out, user_out

router = APIRouter(prefix="/courses", tags=["courses"])
COURSE_TRANSITIONS = {
    "planned": {"active"},
    "active": {"ended"},
    "ended": {"active", "archived"},
    "archived": {"active"},
}


def _ip(request: Request) -> str | None:
    return request.client.host if request.client else None


def _require_admin(user: User, rows, role: str = "admin") -> None:
    if role != "admin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Switch to Administrator to manage courses.")
    require_held_role(user, "admin", rows)


def _require_roster_role(staff_role: str, target_role: str) -> None:
    if target_role == "student":
        require(staff_role, "roster:import", "Your role can't edit the roster.")
    elif target_role == "course_coordinator":
        require(staff_role, "course:manage_access", "Only an administrator can add a course coordinator.")
    elif target_role == "instructor":
        if not (can(staff_role, "instructor:manage") or can(staff_role, "course:manage_access")):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Only a course coordinator or administrator can add instructors.")
    else:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Your role can't edit the roster.")


@router.post("", response_model=CourseOut, response_model_exclude_none=True, status_code=status.HTTP_201_CREATED)
async def create_course(
    body: CourseCreate,
    db: DbSession,
    user: CurrentUser,
    request: Request,
    role: Annotated[str, Query()] = "admin",
):
    rows = await memberships_for(db, user.id)
    _require_admin(user, rows, role)
    require("admin", "course:create", "Your role can't create courses.")
    code = body.code.strip()
    title = body.title.strip()
    term = body.term.strip()
    if not code or not title or not term:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Course code, title, and term are required.")
    if await db.scalar(select(Course.id).where(Course.code == code, Course.term == term)):
        raise HTTPException(status.HTTP_409_CONFLICT, "A course with that code already exists for that term.")
    course = Course(code=code, title=title, term=term, status="planned", inactivity_days=7)
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
        if role and role.code in {"instructor", "course_coordinator"} and row.user_id not in seen:
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
    if not (can(role, "roster:import") or can(role, "case:author")):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Your role can't view the roster.")
    members = (
        await db.scalars(
            select(CourseMembership)
            .where(CourseMembership.course_id == course_id)
            .options(selectinload(CourseMembership.role), selectinload(CourseMembership.discipline))
        )
    ).all()
    payload = []
    seen: set[uuid.UUID] = set()
    for member in members:
        if member.role is None or member.role.code != "student" or member.user_id in seen:
            continue
        person = await db.get(User, member.user_id)
        if person is None:
            continue
        seen.add(person.id)
        payload.append(await _roster_member(db, member, person))
    return payload


@router.post("/{course_id}/roster/import", response_model=RosterImportResult)
async def import_roster(
    course_id: uuid.UUID, body: RosterImport, db: DbSession, user: CurrentUser, request: Request
):
    rows = await memberships_for(db, user.id)
    role = _staff_role(user, rows, course_id)
    _require_roster_role(role, body.role)
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
    reactivated = 0
    passwords: list[TempPassword] = []
    for row in body.rows:
        email = row.email.strip().lower()
        if not email:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Email is required.")
        person = await db.scalar(select(User).where(User.email == email))
        university_id = row.university_id.strip() or None
        if person is None and body.role == "student" and not re.fullmatch(r"800\d{6}", university_id or ""):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"{email} needs a 9-digit 800 number.")
        if person is None:
            first, last = _split_name(row.full_name)
            temporary = secrets.token_urlsafe(9)
            person = User(
                email=email,
                first_name=first,
                last_name=last,
                university_id=university_id,
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
            if existing.deactivated_at is not None:
                existing.deactivated_at = None
                existing.deactivated_by_id = None
                reactivated += 1
            else:
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
        detail=f"{added} {body.role}s added, {reactivated} reactivated, {already} already enrolled",
    )
    await db.commit()
    return RosterImportResult(
        added=added, already_enrolled=already, reactivated=reactivated, temporary_passwords=passwords
    )


@router.post("/{course_id}/enrollments", response_model=PublicUser, response_model_exclude_none=True)
async def enroll_existing(
    course_id: uuid.UUID, body: EnrollmentCreate, db: DbSession, user: CurrentUser, request: Request
):
    rows = await memberships_for(db, user.id)
    _require_roster_role(_staff_role(user, rows, course_id), body.role)
    await ensure_course_open(db, course_id)
    person = await db.get(User, body.user_id)
    if person is None or person.deleted_at is not None or person.purged_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Account not found.")
    if person.archived_at is not None or not person.is_active:
        raise HTTPException(status.HTTP_409_CONFLICT, "Reactivate this account before enrolling it in a class.")
    member_role = await db.scalar(select(Role).where(Role.code == body.role))
    discipline = await db.scalar(select(Discipline).where(Discipline.code == body.discipline))
    if member_role is None or discipline is None:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Roles are not seeded.")
    existing = await db.scalar(
        select(CourseMembership).where(
            CourseMembership.user_id == person.id,
            CourseMembership.course_id == course_id,
            CourseMembership.role_id == member_role.id,
        )
    )
    if existing and existing.deactivated_at is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "This person is already enrolled in the class with that role.")
    if existing:
        existing.deactivated_at = None
        existing.deactivated_by_id = None
        existing.discipline_id = discipline.id
        detail = "reactivated"
    else:
        db.add(
            CourseMembership(
                user_id=person.id,
                course_id=course_id,
                role_id=member_role.id,
                discipline_id=discipline.id,
            )
        )
        detail = "enrolled"
    await log_event(
        db,
        action="roster.enroll",
        entity_type="course",
        entity_id=str(course_id),
        actor_user_id=user.id,
        course_id=course_id,
        ip_address=_ip(request),
        detail=f"{body.role} user/{person.id} {detail}",
    )
    await db.commit()
    return await user_out(db, person)


@router.post("/{course_id}/roster/{user_id}/deactivate", response_model=PublicUser, response_model_exclude_none=True)
async def deactivate_student(
    course_id: uuid.UUID, user_id: uuid.UUID, db: DbSession, user: CurrentUser, request: Request
):
    return await _set_roster_active(course_id, user_id, db, user, request, active=False)


@router.post("/{course_id}/roster/{user_id}/reactivate", response_model=PublicUser, response_model_exclude_none=True)
async def reactivate_student(
    course_id: uuid.UUID, user_id: uuid.UUID, db: DbSession, user: CurrentUser, request: Request
):
    return await _set_roster_active(course_id, user_id, db, user, request, active=True)


@router.delete("/{course_id}/roster/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_from_course(
    course_id: uuid.UUID,
    user_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
    request: Request,
    role: Annotated[Literal["student", "instructor", "course_coordinator"], Query()] = "student",
):
    rows = await memberships_for(db, user.id)
    staff_role = _staff_role(user, rows, course_id)
    if role == "student":
        require(staff_role, "roster:import", "Your role can't edit the roster.")
    elif role == "course_coordinator":
        require(staff_role, "course:manage_access", "Only an administrator can change a course coordinator.")
    else:
        if not (can(staff_role, "instructor:manage") or can(staff_role, "instructor:remove") or can(staff_role, "course:manage_access")):
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Your role can't remove instructors.")
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
    if role != "student" and user_id == user.id:
        raise HTTPException(status.HTTP_409_CONFLICT, "You can't remove yourself from the course.")
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
    course_id: uuid.UUID,
    body: CourseStatusPatch,
    db: DbSession,
    user: CurrentUser,
    request: Request,
    role: Annotated[str, Query()] = "admin",
):
    rows = await memberships_for(db, user.id)
    _require_admin(user, rows, role)
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


@router.patch("/{course_id}/inactivity-days", response_model=CourseOut, response_model_exclude_none=True)
async def set_inactivity_days(
    course_id: uuid.UUID,
    body: InactivityDaysPatch,
    db: DbSession,
    user: CurrentUser,
    request: Request,
    role: Annotated[str, Query()] = "admin",
):
    rows = await memberships_for(db, user.id)
    _require_admin(user, rows, role)
    require("admin", "course:manage_status", "Your role can't change the activity window.")
    course = await db.get(Course, course_id)
    if course is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Course not found.")
    course.inactivity_days = body.days
    await log_event(
        db,
        action="course.inactivity_days",
        entity_type="course",
        entity_id=str(course.id),
        actor_user_id=user.id,
        course_id=course.id,
        ip_address=_ip(request),
        detail=str(body.days),
    )
    await db.commit()
    return course_out(course, [str(person.id) for person in await _instructors(db, course.id)])


@router.patch("/{course_id}/policy", response_model=CourseOut, response_model_exclude_none=True)
async def set_course_policy(
    course_id: uuid.UUID,
    body: CoursePolicyPatch,
    db: DbSession,
    user: CurrentUser,
    request: Request,
    role: Annotated[str, Query()] = "admin",
):
    rows = await memberships_for(db, user.id)
    _require_admin(user, rows, role)
    require("admin", "course:manage_status", "Your role can't change course settings.")
    course = await db.get(Course, course_id)
    if course is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Course not found.")
    if "guardrail_profile" in body.model_fields_set and body.guardrail_profile is not None:
        course.guardrail_profile = body.guardrail_profile
    if "guardrail_mode" in body.model_fields_set:
        course.guardrail_mode = body.guardrail_mode
    if "ai_assist" in body.model_fields_set and body.ai_assist is not None:
        course.ai_assist = body.ai_assist
    await log_event(
        db,
        action="course.policy",
        entity_type="course",
        entity_id=str(course.id),
        actor_user_id=user.id,
        course_id=course.id,
        ip_address=_ip(request),
        detail=body.guardrail_mode or body.guardrail_profile or "",
    )
    await db.commit()
    return course_out(course, [str(person.id) for person in await _instructors(db, course.id)])


async def _roster_member(db, member: CourseMembership, person: User) -> dict:
    payload = await user_out(db, person)
    payload["roster_status"] = "inactive" if member.deactivated_at else "active"
    payload["deactivated_at"] = member.deactivated_at
    if member.deactivated_at and member.discipline is not None:
        course_id = str(member.course_id)
        code = member.discipline.code
        match = next(
            (item for item in payload["roles"] if item["role"] == "student" and item.get("discipline") == code),
            None,
        )
        if match is None:
            payload["roles"].append({"role": "student", "discipline": code, "course_ids": [course_id]})
        elif course_id not in match["course_ids"]:
            match["course_ids"].append(course_id)
    return payload


async def _set_roster_active(course_id, user_id, db, user: User, request: Request, *, active: bool) -> dict:
    rows = await memberships_for(db, user.id)
    action = "roster.reactivate" if active else "roster.deactivate"
    try:
        role = _staff_role(user, rows, course_id)
    except HTTPException:
        role = ""
    if not can(role, "roster:import"):
        await log_event(
            db,
            action=action,
            entity_type="course",
            entity_id=str(course_id),
            actor_user_id=user.id,
            result="denied",
            course_id=course_id,
            ip_address=_ip(request),
            detail="Role cannot change roster access.",
        )
        await db.commit()
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Your role can't edit the roster.")
    await ensure_course_open(db, course_id)
    student_role = await db.scalar(select(Role).where(Role.code == "student"))
    membership = await db.scalar(
        select(CourseMembership)
        .where(
            CourseMembership.user_id == user_id,
            CourseMembership.course_id == course_id,
            CourseMembership.role_id == student_role.id,
        )
        .options(selectinload(CourseMembership.discipline), selectinload(CourseMembership.role))
    )
    if membership is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "That student is not on this roster.")
    if active and membership.deactivated_at is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "This student is already active in this course.")
    if not active and membership.deactivated_at is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "This student is already inactive in this course.")
    membership.deactivated_at = None if active else datetime.now(timezone.utc)
    membership.deactivated_by_id = None if active else user.id
    person = await db.get(User, user_id)
    await log_event(
        db,
        action=action,
        entity_type="course",
        entity_id=str(course_id),
        actor_user_id=user.id,
        course_id=course_id,
        ip_address=_ip(request),
        detail=f"student user/{user_id}",
    )
    await db.commit()
    await db.refresh(membership, attribute_names=["deactivated_at", "discipline", "role"])
    return await _roster_member(db, membership, person)


@router.post("/{course_id}/grading-guide", response_model=CourseOut, response_model_exclude_none=True)
async def upload_grading_guide(
    course_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
    request: Request,
    file: UploadFile = File(...),
):
    rows = await memberships_for(db, user.id)
    role = _staff_role(user, rows, course_id)
    if not (can(role, "case:author") or can(role, "course:manage_access")):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Your role can't upload a rubric.")
    course = await ensure_course_open(db, course_id)
    payload = await file.read()
    if len(payload) > 8_000_000:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "Rubric files must be 8 MB or smaller.")
    course.grading_guide = guide_from_upload(file.filename or "rubric.pdf", payload)
    course.rubric_file_name = course.grading_guide["file_name"]
    await log_event(
        db,
        action="course.grading_guide",
        entity_type="course",
        entity_id=str(course.id),
        actor_user_id=user.id,
        course_id=course.id,
        ip_address=_ip(request),
        detail=course.rubric_file_name,
    )
    await db.commit()
    return course_out(course, [str(person.id) for person in await _instructors(db, course.id)])


def _staff_role(user: User, rows, course_id: uuid.UUID) -> str:
    if any(item.code == "admin" for item in user.roles):
        return "admin"
    if any(row.role.code == "course_coordinator" and row.course_id == course_id for row in rows):
        require_course("course_coordinator", course_id, user, rows)
        return "course_coordinator"
    if any(row.role.code == "instructor" and row.course_id == course_id for row in rows):
        require_course("instructor", course_id, user, rows)
        return "instructor"
    raise HTTPException(status.HTTP_403_FORBIDDEN, "Your role can't view the roster.")


def _split_name(full_name: str) -> tuple[str, str]:
    cleaned = " ".join(full_name.split())
    if " " not in cleaned:
        return cleaned, cleaned
    first, last = cleaned.rsplit(" ", 1)
    return first, last
