import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.clinical import ClinicalNote, CourseMembership, NoteAddendum, NoteComment, Patient
from app.models.user import Discipline, Role, User
from app.services.access import can, require
from app.services.audit import log_event
from app.services.note_prefill import diagnoses_from_patient, prefill_from_patient
from app.services.charts import utcnow

EDITABLE = {"draft", "returned"}


async def load_note(db: AsyncSession, note_id: uuid.UUID) -> ClinicalNote:
    note = await db.get(ClinicalNote, note_id)
    if note is None or note.archived:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Note not found.")
    return note


def ensure_can_read(note: ClinicalNote, user: User, role: str) -> None:
    if role == "student" and note.author_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You can only open notes you wrote.")


async def create_draft(
    db: AsyncSession,
    *,
    author: User,
    patient: Patient,
    template_id: str,
    discipline_code: str,
    role: str,
    ip: str | None,
) -> ClinicalNote:
    require(role, "note:author", "Your role can't write notes.")
    if patient.encounter is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "This chart has no encounter to attach a note to.")
    discipline = await db.scalar(select(Discipline).where(Discipline.code == discipline_code))
    if discipline is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Unknown discipline.")
    note = ClinicalNote(
        patient_id=patient.id,
        encounter_id=patient.encounter.id,
        template_id=template_id,
        author_id=author.id,
        discipline_id=discipline.id,
        mode=patient.mode,
        status="draft",
        version=1,
        content=prefill_from_patient(template_id, patient),
        diagnoses=diagnoses_from_patient(patient),
    )
    db.add(note)
    await db.flush()
    await log_event(
        db,
        action="note.create",
        entity_type="note",
        entity_id=str(note.id),
        actor_user_id=author.id,
        course_id=patient.course_id,
        ip_address=ip,
    )
    return await load_note(db, note.id)


async def save_draft(db, note: ClinicalNote, author: User, expected_version: int, patch: dict) -> ClinicalNote:
    if note.author_id != author.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only the author can edit this note.")
    if note.status not in EDITABLE:
        raise HTTPException(status.HTTP_409_CONFLICT, "This note is signed. Add an addendum instead.")
    _check_version(note, expected_version)
    if patch.get("template_id"):
        note.template_id = patch["template_id"]
    if patch.get("content") is not None:
        note.content = patch["content"]
    if patch.get("diagnoses") is not None:
        note.diagnoses = patch["diagnoses"]
    if "routed_to_id" in patch and patch["routed_to_id"] is not None:
        note.routed_to_id = patch["routed_to_id"]
    note.version += 1
    note.updated_at = utcnow()
    await db.flush()
    return note


async def sign_note(db, note: ClinicalNote, author: User, expected_version: int, ip: str | None, course_id) -> ClinicalNote:
    if note.author_id != author.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only the author can sign this note.")
    if note.status not in EDITABLE:
        raise HTTPException(status.HTTP_409_CONFLICT, "This note is signed. Add an addendum instead.")
    _check_version(note, expected_version)
    if note.mode == "assessment" and note.routed_to_id is None:
        instructor_id = await db.scalar(
            select(CourseMembership.user_id)
            .join(Role, Role.id == CourseMembership.role_id)
            .where(CourseMembership.course_id == course_id, Role.code == "instructor")
            .limit(1)
        )
        if instructor_id is None:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Choose an instructor to review this note.")
        note.routed_to_id = instructor_id
    note.status = "pending_review" if note.mode == "assessment" else "signed"
    note.signed_at = utcnow()
    note.updated_at = note.signed_at
    note.version += 1
    await log_event(
        db,
        action="note.sign_submit" if note.mode == "assessment" else "note.sign",
        entity_type="note",
        entity_id=str(note.id),
        actor_user_id=author.id,
        course_id=course_id,
        ip_address=ip,
    )
    return note


async def cosign_note(db, note: ClinicalNote, reviewer: User, role: str, comment: str | None, ip: str | None, course_id) -> None:
    if not can(role, "note:cosign"):
        await log_event(
            db,
            action="note.cosign",
            entity_type="note",
            entity_id=str(note.id),
            actor_user_id=reviewer.id,
            result="denied",
            course_id=course_id,
            ip_address=ip,
            detail="Role lacks co-signature authority (403).",
        )
        await db.commit()
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Your role can't co-sign notes.")
    if note.status != "pending_review":
        raise HTTPException(status.HTTP_409_CONFLICT, "Only notes pending review can be co-signed.")
    note.status = "cosigned"
    note.cosigned_at = utcnow()
    note.cosigned_by_id = reviewer.id
    note.updated_at = note.cosigned_at
    note.version += 1
    if comment and comment.strip():
        db.add(
            NoteComment(
                note_id=note.id,
                author_id=reviewer.id,
                body=comment.strip(),
                kind="cosigned",
                created_at=note.cosigned_at,
            )
        )
    await log_event(
        db,
        action="note.cosign",
        entity_type="note",
        entity_id=str(note.id),
        actor_user_id=reviewer.id,
        course_id=course_id,
        ip_address=ip,
    )


async def return_note(db, note: ClinicalNote, reviewer: User, role: str, comment: str, ip: str | None, course_id) -> None:
    require(role, "note:cosign", "Your role can't return notes.")
    if not comment.strip():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Tell the student what to revise.")
    if note.status != "pending_review":
        raise HTTPException(status.HTTP_409_CONFLICT, "Only notes pending review can be returned.")
    now = utcnow()
    note.status = "returned"
    note.updated_at = now
    note.version += 1
    db.add(NoteComment(note_id=note.id, author_id=reviewer.id, body=comment.strip(), kind="returned", created_at=now))
    await log_event(
        db,
        action="note.return",
        entity_type="note",
        entity_id=str(note.id),
        actor_user_id=reviewer.id,
        course_id=course_id,
        ip_address=ip,
    )


async def add_addendum(db, note: ClinicalNote, author: User, body: str, ip: str | None, course_id) -> None:
    if note.status not in {"signed", "cosigned"}:
        raise HTTPException(status.HTTP_409_CONFLICT, "Addenda are for signed notes. Edit the draft instead.")
    now = utcnow()
    db.add(NoteAddendum(note_id=note.id, author_id=author.id, body=body.strip(), created_at=now))
    note.updated_at = now
    note.version += 1
    await log_event(
        db,
        action="note.addendum",
        entity_type="note",
        entity_id=str(note.id),
        actor_user_id=author.id,
        course_id=course_id,
        ip_address=ip,
    )


def _check_version(note: ClinicalNote, expected: int) -> None:
    if note.version != expected:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "This note was changed in another window. Reload to see the latest version before editing.",
        )
