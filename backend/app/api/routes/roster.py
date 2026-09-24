import re
import uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser, DbSession
from app.core.security import hash_password
from app.models.course import Enrollment
from app.models.user import Discipline, Role, User
from app.schemas.clinical import (
    RosterImportIn,
    RosterImportOut,
    RosterMemberIn,
    RosterMemberOut,
    SessionUserOut,
)
from app.services.access import can_manage_roster, list_enrollments
from app.services.audit import log_event
from app.services.serializers import session_user_from

router = APIRouter(prefix="/courses/{course_id}/roster", tags=["roster"])

TEMP_PASSWORD = "ChangeMe1!"
ALLOWED_EMAIL = ("@utep.edu", "@miners.utep.edu")
UNI_RE = re.compile(r"^800\d{6}$")


def _assert_utep_email(email: str) -> str:
    lowered = email.strip().lower()
    if not any(lowered.endswith(sfx) for sfx in ALLOWED_EMAIL):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Use a UTEP email (@utep.edu or @miners.utep.edu).",
        )
    return lowered


def _parse_name(full_name: str) -> tuple[str, str]:
    parts = full_name.strip().split(None, 1)
    first = parts[0] if parts else "Student"
    last = parts[1] if len(parts) > 1 else ""
    return first, last


async def _role_by_code(db: DbSession, code: str) -> Role | None:
    return (
        await db.execute(select(Role).options(selectinload(Role.permissions)).where(Role.code == code))
    ).scalar_one_or_none()


@router.get("", response_model=list[SessionUserOut])
async def list_roster(course_id: uuid.UUID, user: CurrentUser, db: DbSession):
    if not can_manage_roster(user):
        raise HTTPException(status_code=403, detail="Not allowed to view roster")
    rows = (
        await db.execute(
            select(Enrollment).where(
                Enrollment.course_id == course_id,
                Enrollment.app_role.in_(("student", "instructor")),
            )
        )
    ).scalars().all()
    out: list[SessionUserOut] = []
    seen: set[uuid.UUID] = set()
    for e in rows:
        if e.user_id in seen:
            continue
        seen.add(e.user_id)
        u = await db.get(
            User,
            e.user_id,
            options=(selectinload(User.roles).selectinload(Role.permissions), selectinload(User.discipline)),
        )
        if u is None:
            continue
        enrollments = await list_enrollments(db, u.id)
        out.append(session_user_from(u, enrollments))
    return out


@router.post("/members", response_model=RosterMemberOut, status_code=status.HTTP_201_CREATED)
async def add_member(course_id: uuid.UUID, body: RosterMemberIn, user: CurrentUser, db: DbSession):
    """Add one student or instructor to the course (requires user:manage)."""
    if not can_manage_roster(user):
        raise HTTPException(status_code=403, detail="Not allowed to add users")

    email = _assert_utep_email(str(body.email))
    uni = (body.universityId or "").strip() or None
    if uni and not UNI_RE.match(uni):
        raise HTTPException(status_code=400, detail="800 number must look like 800123456.")

    app_role = body.appRole
    if app_role not in ("student", "instructor"):
        raise HTTPException(status_code=400, detail="Role must be student or instructor.")

    role = await _role_by_code(db, app_role)
    discipline = (
        await db.execute(select(Discipline).where(Discipline.code == body.discipline))
    ).scalar_one_or_none()
    if app_role == "student" and discipline is None:
        raise HTTPException(status_code=400, detail="Unknown discipline.")

    first, last = _parse_name(body.fullName)
    existing = (
        await db.execute(
            select(User)
            .options(selectinload(User.roles).selectinload(Role.permissions), selectinload(User.discipline))
            .where(User.email == email)
        )
    ).scalar_one_or_none()
    created = False
    if existing is None:
        existing = User(
            email=email,
            first_name=first,
            last_name=last,
            hashed_password=hash_password(TEMP_PASSWORD),
            must_change_password=True,
            university_id=uni,
            discipline_id=discipline.id if discipline else None,
            roles=[role] if role else [],
        )
        db.add(existing)
        await db.flush()
        created = True
    else:
        if uni and not existing.university_id:
            existing.university_id = uni
        if role and all(r.id != role.id for r in existing.roles):
            existing.roles.append(role)

    disc_code = body.discipline if app_role == "student" else None
    enr_q = select(Enrollment).where(
        Enrollment.user_id == existing.id,
        Enrollment.course_id == course_id,
        Enrollment.app_role == app_role,
    )
    if disc_code is None:
        enr_q = enr_q.where(Enrollment.discipline_code.is_(None))
    else:
        enr_q = enr_q.where(Enrollment.discipline_code == disc_code)
    enr = (await db.execute(enr_q)).scalar_one_or_none()
    already = enr is not None
    if not already:
        db.add(
            Enrollment(
                user_id=existing.id,
                course_id=course_id,
                app_role=app_role,
                discipline_code=disc_code,
            )
        )

    await log_event(
        db,
        action="roster.add_member",
        entity_type="course",
        actor_user_id=user.id,
        entity_id=str(course_id),
        details={"email": email, "appRole": app_role, "created": created, "alreadyEnrolled": already},
    )
    await db.commit()

    enrollments = await list_enrollments(db, existing.id)
    # reload with relationships
    existing = await db.get(
        User,
        existing.id,
        options=(selectinload(User.roles).selectinload(Role.permissions), selectinload(User.discipline)),
    )
    assert existing is not None
    return RosterMemberOut(
        created=created,
        alreadyEnrolled=already,
        user=session_user_from(existing, enrollments),
    )


@router.post("/import", response_model=RosterImportOut)
async def import_roster(course_id: uuid.UUID, body: RosterImportIn, user: CurrentUser, db: DbSession):
    if not can_manage_roster(user):
        raise HTTPException(status_code=403, detail="Not allowed to import roster")
    if any(r.get("problem") for r in body.rows):
        raise HTTPException(status_code=400, detail="Fix the flagged rows before importing.")

    student_role = await _role_by_code(db, "student")
    discipline = (
        await db.execute(select(Discipline).where(Discipline.code == body.discipline))
    ).scalar_one_or_none()

    added = 0
    already = 0
    for row in body.rows:
        email = row["email"].strip().lower()
        full_name = row["fullName"].strip()
        university_id = row.get("universityId", "").strip() or None
        first, last = _parse_name(full_name)

        existing = (await db.execute(select(User).where(User.email == email))).scalar_one_or_none()
        if existing is None:
            existing = User(
                email=email,
                first_name=first,
                last_name=last,
                hashed_password=hash_password(TEMP_PASSWORD),
                must_change_password=True,
                university_id=university_id,
                discipline_id=discipline.id if discipline else None,
                roles=[student_role] if student_role else [],
            )
            db.add(existing)
            await db.flush()

        enr = (
            await db.execute(
                select(Enrollment).where(
                    Enrollment.user_id == existing.id,
                    Enrollment.course_id == course_id,
                    Enrollment.app_role == "student",
                    Enrollment.discipline_code == body.discipline,
                )
            )
        ).scalar_one_or_none()
        if enr:
            already += 1
        else:
            db.add(
                Enrollment(
                    user_id=existing.id,
                    course_id=course_id,
                    app_role="student",
                    discipline_code=body.discipline,
                )
            )
            added += 1

    await log_event(
        db,
        action="roster.import",
        entity_type="course",
        actor_user_id=user.id,
        entity_id=str(course_id),
        details={"added": added, "alreadyEnrolled": already},
    )
    await db.commit()
    return RosterImportOut(added=added, alreadyEnrolled=already)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_from_course(course_id: uuid.UUID, user_id: uuid.UUID, user: CurrentUser, db: DbSession):
    if not can_manage_roster(user):
        raise HTTPException(status_code=403, detail="Not allowed")
    rows = (
        await db.execute(
            select(Enrollment).where(
                Enrollment.course_id == course_id,
                Enrollment.user_id == user_id,
            )
        )
    ).scalars().all()
    for r in rows:
        await db.delete(r)
    await log_event(
        db,
        action="roster.remove",
        entity_type="course",
        actor_user_id=user.id,
        entity_id=str(course_id),
        details={"user": str(user_id)},
    )
    await db.commit()
