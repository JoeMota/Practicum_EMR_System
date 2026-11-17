import uuid

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.clinical import ClinicalNote, NoteAddendum, NoteComment, Patient
from app.models.user import Discipline, User
from app.services.access import can, require
from app.services.audit import log_event
from app.services.note_prefill import diagnoses_from_patient, prefill_from_patient
from app.services.charts import utcnow
from app.services.note_crypto import seal_note, seal_text
from app.services.note_templates import allowed_section_ids, assert_usable, template_sensitivity
from app.services.simulation import may_edit_simulation_note, prepare_note, sign_simulation

CONTENT_LIMIT = 20_000

EDITABLE = {"draft", "returned"}


async def load_note(db: AsyncSession, note_id: uuid.UUID) -> ClinicalNote:
    note = await db.get(ClinicalNote, note_id)
    if note is None or note.archived:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Note not found.")
    return note


def _bounded_content(content: dict) -> dict:
    if not isinstance(content, dict):
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Note content must be a set of fields.")
    for key, value in content.items():
        if not isinstance(key, str) or len(key) > 40:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "A note field name is too long.")
        if isinstance(value, str) and len(value) > CONTENT_LIMIT:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "A note field is too long.")
    return content


def ensure_can_read(note: ClinicalNote, user: User, role: str) -> None:
    if role == "student" and note.author_id != user.id and note.mode != "simulation":
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
    kind: str = "visit",
) -> ClinicalNote:
    require(role, "note:author", "Your role can't write notes.")
    kind = await prepare_note(db, patient, author, role, kind)
    if patient.mode == "case":
        raise HTTPException(status.HTTP_409_CONFLICT, "Edit the case instead of writing a note on the master.")
    if patient.encounter is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "This chart has no encounter to attach a note to.")
    discipline = await db.scalar(select(Discipline).where(Discipline.code == discipline_code))
    if discipline is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Unknown discipline.")
    await assert_usable(db, template_id, patient.course_id)
    sensitivity = await template_sensitivity(db, template_id)
    note = ClinicalNote(
        patient_id=patient.id,
        encounter_id=patient.encounter.id,
        template_id=template_id,
        sensitive=sensitivity != "standard",
        sensitivity=sensitivity,
        author_id=author.id,
        discipline_id=discipline.id,
        mode=patient.mode,
        kind=kind,
        status="draft",
        version=1,
        content=prefill_from_patient(template_id, patient),
        diagnoses=diagnoses_from_patient(patient),
    )
    db.add(note)
    await db.flush()
    seal_note(note)
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
    closed = note.status not in EDITABLE or note.body_locked
    shared = await may_edit_simulation_note(db, note, author)
    if note.author_id != author.id and not shared:
        if note.mode == "simulation" and closed:
            raise HTTPException(status.HTTP_409_CONFLICT, "This note is closed. Start a clarification note instead.")
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only the author can edit this note.")
    if closed:
        message = "This note is closed. Start a clarification note instead." if note.mode == "simulation" else "This note is signed. Add an addendum instead of changing it."
        raise HTTPException(status.HTTP_409_CONFLICT, message)
    _check_version(note, expected_version)
    if patch.get("template_id"):
        patient = await db.get(Patient, note.patient_id)
        if patient is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "This patient doesn't exist or was archived.")
        await assert_usable(db, patch["template_id"], patient.course_id)
        note.template_id = patch["template_id"]
        note.sensitivity = await template_sensitivity(db, note.template_id)
        note.sensitive = note.sensitivity != "standard"
    if patch.get("content") is not None:
        note.content = _bounded_content(patch["content"])
    seal_note(note)
    if patch.get("diagnoses") is not None:
        note.diagnoses = patch["diagnoses"]
    if patch.get("cpt_codes") is not None:
        note.cpt_codes = patch["cpt_codes"]
    if "routed_to_id" in patch and patch["routed_to_id"] is not None:
        note.routed_to_id = patch["routed_to_id"]
    note.version += 1
    note.updated_at = utcnow()
    await db.flush()
    return note


async def sign_note(db, note: ClinicalNote, author: User, expected_version: int, ip: str | None, course_id) -> ClinicalNote:
    if note.mode == "simulation":
        if note.status not in EDITABLE or note.body_locked:
            raise HTTPException(status.HTTP_409_CONFLICT, "This note is closed. Start a clarification note instead.")
        _check_version(note, expected_version)
        patient = await db.get(Patient, note.patient_id)
        if patient is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "This patient doesn't exist or was archived.")
        await sign_simulation(db, note, author, patient)
        note.signed_at = utcnow()
        note.updated_at = note.signed_at
        note.version += 1
        await log_event(
            db,
            action="note.sign",
            entity_type="note",
            entity_id=str(note.id),
            actor_user_id=author.id,
            course_id=course_id,
            ip_address=ip,
        )
        return note
    if note.author_id != author.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only the author can sign this note.")
    if note.status not in EDITABLE:
        raise HTTPException(status.HTTP_409_CONFLICT, "This note is signed. Add an addendum instead.")
    if note.body_locked:
        raise HTTPException(status.HTTP_409_CONFLICT, "This note is signed. Add an addendum instead of changing it.")
    _check_version(note, expected_version)
    if note.mode == "assessment" and note.routed_to_id is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Choose an instructor to review this note.")
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
    note.body_locked = True
    note.cosigned_at = utcnow()
    note.cosigned_by_id = reviewer.id
    note.updated_at = note.cosigned_at
    note.version += 1
    if comment and comment.strip():
        body, cipher = seal_text(note, comment.strip())
        db.add(
            NoteComment(
                note_id=note.id,
                author_id=reviewer.id,
                body=body,
                body_cipher=cipher,
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
    body, cipher = seal_text(note, comment.strip())
    db.add(NoteComment(note_id=note.id, author_id=reviewer.id, body=body, body_cipher=cipher, kind="returned", created_at=now))
    await log_event(
        db,
        action="note.return",
        entity_type="note",
        entity_id=str(note.id),
        actor_user_id=reviewer.id,
        course_id=course_id,
        ip_address=ip,
    )


async def add_section_comment(
    db,
    note: ClinicalNote,
    reviewer: User,
    role: str,
    section_id: str | None,
    body: str,
    ip: str | None,
    course_id,
) -> None:
    if not can(role, "note:cosign"):
        await log_event(
            db,
            action="note.comment",
            entity_type="note",
            entity_id=str(note.id),
            actor_user_id=reviewer.id,
            result="denied",
            course_id=course_id,
            ip_address=ip,
            detail="Role cannot comment on notes.",
        )
        await db.commit()
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Your role can't comment on notes.")
    if note.status != "pending_review":
        raise HTTPException(status.HTTP_409_CONFLICT, "Comments can be added while a note is pending review.")
    if section_id and section_id not in await allowed_section_ids(db, note.template_id):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "That section isn't on this note.")
    text = body.strip()
    if not text:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Write a comment before saving.")
    if len(text) > CONTENT_LIMIT:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "That comment is too long.")
    stored, cipher = seal_text(note, text)
    now = utcnow()
    db.add(
        NoteComment(
            note_id=note.id,
            author_id=reviewer.id,
            body=stored,
            body_cipher=cipher,
            kind="comment",
            section_id=section_id,
            created_at=now,
        )
    )
    await log_event(
        db,
        action="note.comment",
        entity_type="note",
        entity_id=str(note.id),
        actor_user_id=reviewer.id,
        course_id=course_id,
        ip_address=ip,
        detail=section_id or "whole note",
    )


async def instructor_edit_note(db, note: ClinicalNote, reviewer: User, role: str, patch: dict, ip: str | None, course_id) -> None:
    require(role, "note:cosign", "Your role can't edit a student note.")
    if note.body_locked:
        raise HTTPException(status.HTTP_409_CONFLICT, "This note is already signed. Return it or review the addendum.")
    if note.status != "pending_review":
        raise HTTPException(status.HTTP_409_CONFLICT, "Edit a note while it is pending review, or return it to the student.")
    if patch.get("content") is not None:
        note.content = _bounded_content(patch["content"])
    seal_note(note)
    if patch.get("diagnoses") is not None:
        note.diagnoses = patch["diagnoses"]
    if patch.get("cpt_codes") is not None:
        note.cpt_codes = patch["cpt_codes"]
    note.version += 1
    note.updated_at = utcnow()
    await log_event(
        db,
        action="note.instructor_edit",
        entity_type="note",
        entity_id=str(note.id),
        actor_user_id=reviewer.id,
        course_id=course_id,
        ip_address=ip,
    )


async def save_scores(db, note: ClinicalNote, reviewer: User, role: str, scores: dict, ip: str | None, course_id) -> None:
    require(role, "note:cosign", "Your role can't grade notes.")
    if note.status not in {"pending_review", "cosigned"}:
        raise HTTPException(status.HTTP_409_CONFLICT, "Score a note while it is in review or after co-signature.")
    note.rubric_scores = scores
    note.updated_at = utcnow()
    await log_event(
        db,
        action="note.score",
        entity_type="note",
        entity_id=str(note.id),
        actor_user_id=reviewer.id,
        course_id=course_id,
        ip_address=ip,
    )


async def add_addendum(db, note: ClinicalNote, author: User, body: str, ip: str | None, course_id) -> None:
    if note.mode == "simulation":
        raise HTTPException(status.HTTP_409_CONFLICT, "This note is closed. Start a clarification note instead.")
    if note.author_id != author.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only the author can add an addendum.")
    revisable = note.status in {"signed", "cosigned"} or (note.status == "returned" and note.body_locked)
    if not revisable:
        raise HTTPException(status.HTTP_409_CONFLICT, "Addenda are for signed notes. Edit the draft instead.")
    text = body.strip()
    if len(text) > CONTENT_LIMIT:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "That addendum is too long.")
    stored, cipher = seal_text(note, text)
    now = utcnow()
    db.add(NoteAddendum(note_id=note.id, author_id=author.id, body=stored, body_cipher=cipher, created_at=now))
    note.updated_at = now
    note.version += 1
    if note.mode == "assessment":
        note.status = "pending_review"
        note.body_locked = True
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
