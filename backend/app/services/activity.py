"""Per-student chart time and at-risk flags. Case chart content is not exported."""

import uuid
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from fastapi import HTTPException, status
from openpyxl import Workbook
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditEvent
from app.models.clinical import ChartSession, ClinicalNote, Course, CourseMembership, Patient
from app.models.user import Role, User
from app.services.access import full_name
from app.services.charts import utcnow
from app.services.teaching_exports import _sheet_bytes

SUBMITTED = {"pending_review", "returned", "cosigned", "signed"}
COUNTED_ACTIONS = ("chart.view", "note.create", "note.sign", "note.sign_submit")
CAMPUS = ZoneInfo("America/Denver")


def window(start: date, end: date) -> tuple[datetime, datetime]:
    if end < start:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "The end date is before the start date.")
    start_at = datetime.combine(start, time.min, tzinfo=CAMPUS)
    end_at = datetime.combine(end, time.max, tzinfo=CAMPUS)
    return start_at, end_at


def _aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value


def _overlaps(began: datetime, seen: datetime, start_at: datetime, end_at: datetime) -> bool:
    return seen >= start_at and began <= end_at


async def _students(db: AsyncSession, course_id: uuid.UUID) -> list[User]:
    return list(
        (
            await db.scalars(
                select(User)
                .join(CourseMembership, CourseMembership.user_id == User.id)
                .join(Role, Role.id == CourseMembership.role_id)
                .where(
                    CourseMembership.course_id == course_id,
                    CourseMembership.deactivated_at.is_(None),
                    Role.code == "student",
                    User.purged_at.is_(None),
                )
                .order_by(User.last_name, User.first_name)
            )
        ).all()
    )


async def activity_rows(db: AsyncSession, course_id: uuid.UUID, start: date, end: date) -> list[dict]:
    start_at, end_at = window(start, end)
    people = await _students(db, course_id)
    sessions = list(
        (await db.scalars(select(ChartSession).where(ChartSession.course_id == course_id))).all()
    )
    events = list(
        (
            await db.scalars(
                select(AuditEvent).where(
                    AuditEvent.course_id == course_id,
                    AuditEvent.result == "ok",
                    AuditEvent.occurred_at >= start_at,
                    AuditEvent.occurred_at <= end_at,
                    AuditEvent.action.in_(COUNTED_ACTIONS),
                )
            )
        ).all()
    )
    rows = []
    for person in people:
        own_sessions = []
        minutes = 0.0
        for item in sessions:
            if item.user_id != person.id:
                continue
            began = _aware(item.started_at)
            seen = _aware(item.last_seen_at)
            if not _overlaps(began, seen, start_at, end_at):
                continue
            own_sessions.append(item)
            left = max(began, start_at)
            right = min(seen, end_at)
            minutes += max(0, (right - left).total_seconds())
        own_events = [item for item in events if item.actor_user_id == person.id]
        rows.append(
            {
                "user_id": str(person.id),
                "student": full_name(person),
                "last_sign_in": person.last_login_at,
                "sessions": len(own_sessions),
                "active_minutes": round(minutes / 60, 1),
                "charts_opened": sum(1 for item in own_events if item.action == "chart.view"),
                "notes_started": sum(1 for item in own_events if item.action == "note.create"),
                "notes_submitted": sum(1 for item in own_events if item.action in {"note.sign", "note.sign_submit"}),
            }
        )
    return rows


def workbook_for(rows_by_course: list[tuple[str, list[dict]]]) -> bytes:
    book = Workbook()
    sheet = book.active
    sheet.title = "Student activity"
    sheet.append(
        [
            "Course",
            "Student",
            "Last sign-in",
            "Sessions",
            "Active minutes",
            "Charts opened",
            "Notes started",
            "Notes submitted",
        ]
    )
    wrote = False
    for course_code, rows in rows_by_course:
        if not rows:
            sheet.append([course_code, "No students enrolled", "", 0, 0, 0, 0, 0])
            wrote = True
            continue
        for row in rows:
            signed_in = row["last_sign_in"]
            sheet.append(
                [
                    course_code,
                    row["student"],
                    signed_in.isoformat() if signed_in else "",
                    row["sessions"],
                    row["active_minutes"],
                    row["charts_opened"],
                    row["notes_started"],
                    row["notes_submitted"],
                ]
            )
            wrote = True
    if not wrote:
        sheet.append(["No courses", "", "", 0, 0, 0, 0, 0])
    return _sheet_bytes(book)


async def at_risk(db: AsyncSession, course_id: uuid.UUID) -> dict:
    course = await db.get(Course, course_id)
    if course is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Course not found.")
    days = course.inactivity_days or 7
    cutoff = utcnow() - timedelta(days=days)
    people = await _students(db, course_id)
    sessions = list(
        (await db.scalars(select(ChartSession).where(ChartSession.course_id == course_id))).all()
    )
    latest: dict[uuid.UUID, datetime] = {}
    for item in sessions:
        seen = _aware(item.last_seen_at)
        current = latest.get(item.user_id)
        if current is None or seen > current:
            latest[item.user_id] = seen
    assigned = list(
        (
            await db.scalars(
                select(Patient).where(
                    Patient.course_id == course_id,
                    Patient.owner_id.is_not(None),
                    Patient.deleted_at.is_(None),
                    Patient.mode != "case",
                )
            )
        ).all()
    )
    owner_ids = {patient.owner_id for patient in assigned}
    notes = list(
        (
            await db.scalars(
                select(ClinicalNote).where(
                    ClinicalNote.patient_id.in_([patient.id for patient in assigned] or [uuid.uuid4()]),
                    ClinicalNote.archived.is_(False),
                )
            )
        ).all()
    ) if assigned else []
    submitted = {
        note.author_id
        for note in notes
        if note.status in SUBMITTED and note.author_id in owner_ids
    }
    flagged = []
    idle = f"No chart activity for {days} days"
    missing = "Assigned chart with no submitted note"
    for person in people:
        reasons = []
        seen = latest.get(person.id)
        if seen is None or seen < cutoff:
            reasons.append(idle)
        if person.id in owner_ids and person.id not in submitted:
            reasons.append(missing)
        if reasons:
            flagged.append({"user_id": str(person.id), "student": full_name(person), "reasons": reasons})
    return {"days": days, "students": flagged}
