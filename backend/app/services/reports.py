import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditEvent
from app.models.clinical import ClinicalNote, CourseMembership, Patient
from app.models.user import Role

NOTE_STATUSES = ("draft", "pending_review", "signed", "cosigned", "returned")
PATIENT_MODES = ("practice", "assessment")


async def course_report(db: AsyncSession, course_id: uuid.UUID) -> dict:
    students = await db.scalar(
        select(func.count(func.distinct(CourseMembership.user_id)))
        .join(Role, Role.id == CourseMembership.role_id)
        .where(CourseMembership.course_id == course_id, Role.code == "student")
    )
    notes_by_status = dict.fromkeys(NOTE_STATUSES, 0)
    for note_status, count in (
        await db.execute(
            select(ClinicalNote.status, func.count(ClinicalNote.id))
            .join(Patient, Patient.id == ClinicalNote.patient_id)
            .where(Patient.course_id == course_id, Patient.deleted_at.is_(None), ClinicalNote.archived.is_(False))
            .group_by(ClinicalNote.status)
        )
    ).all():
        if note_status in notes_by_status:
            notes_by_status[note_status] = count

    patients_by_mode = dict.fromkeys(PATIENT_MODES, 0)
    for mode, count in (
        await db.execute(
            select(Patient.mode, func.count(Patient.id))
            .where(Patient.course_id == course_id, Patient.deleted_at.is_(None))
            .group_by(Patient.mode)
        )
    ).all():
        if mode in patients_by_mode:
            patients_by_mode[mode] = count

    audit_by_action = dict(
        (
            await db.execute(
                select(AuditEvent.action, func.count(AuditEvent.id))
                .where(AuditEvent.course_id == course_id)
                .group_by(AuditEvent.action)
                .order_by(AuditEvent.action)
            )
        ).all()
    )
    return {
        "course_id": str(course_id),
        "students_enrolled": students or 0,
        "notes_by_status": notes_by_status,
        "patients_by_mode": patients_by_mode,
        "audit_event_count": sum(audit_by_action.values()),
        "audit_events_by_action": audit_by_action,
    }