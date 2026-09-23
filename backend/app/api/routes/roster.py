import uuid

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser, DbSession
from app.core.security import hash_password
from app.models.course import Enrollment
from app.models.user import Discipline, Role, User
from app.schemas.clinical import RosterImportIn, RosterImportOut, SessionUserOut
from app.services.access import can_manage_roster, list_enrollments
from app.services.audit import log_event
from app.services.serializers import session_user_from

router = APIRouter(prefix="/courses/{course_id}/roster", tags=["roster"])

TEMP_PASSWORD = "ChangeMe1!"


@router.get("", response_model=list[SessionUserOut])
async def list_roster(course_id: uuid.UUID, user: CurrentUser, db: DbSession):
    rows = (
        await db.execute(
            select(Enrollment).where(
                Enrollment.course_id == course_id,
                Enrollment.app_role == "student",
            )
        )
    ).scalars().all()
    out: list[SessionUserOut] = []
    seen: set[uuid.UUID] = set()
    for e in rows:
        if e.user_id in seen:
            continue
        seen.add(e.user_id)
        u = await db.get(User, e.user_id)
        if u is None:
            continue
        enrollments = await list_enrollments(db, u.id)
        out.append(session_user_from(u, enrollments))
    return out


@router.post("/import", response_model=RosterImportOut)
async def import_roster(course_id: uuid.UUID, body: RosterImportIn, user: CurrentUser, db: DbSession):
    if not can_manage_roster(user):
        raise HTTPException(status_code=403, detail="Not allowed to import roster")
    if any(r.get("problem") for r in body.rows):
        raise HTTPException(status_code=400, detail="Fix the flagged rows before importing.")

    student_role = (
        await db.execute(select(Role).options(selectinload(Role.permissions)).where(Role.code == "student"))
    ).scalar_one_or_none()
    discipline = (
        await db.execute(select(Discipline).where(Discipline.code == body.discipline))
    ).scalar_one_or_none()

    added = 0
    already = 0
    for row in body.rows:
        email = row["email"].strip().lower()
        full_name = row["fullName"].strip()
        university_id = row.get("universityId", "").strip() or None
        parts = full_name.split(None, 1)
        first = parts[0] if parts else "Student"
        last = parts[1] if len(parts) > 1 else ""

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
                Enrollment.app_role == "student",
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
