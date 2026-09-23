import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession
from app.models.note import ClinicalNote
from app.models.patient import Patient
from app.schemas.clinical import (
    ClinicalNoteOut,
    CreateNoteIn,
    DraftPatchIn,
    NoteActionIn,
    QueueItemOut,
)
from app.services.access import can_cosign, require_app_role
from app.services.audit import log_event
from app.services.serializers import note_out, patient_out

router = APIRouter(prefix="/notes", tags=["notes"])


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def _get_note(db: DbSession, note_id: uuid.UUID) -> ClinicalNote:
    n = await db.get(ClinicalNote, note_id)
    if n is None or n.archived or n.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found.")
    return n


async def _require_role_for_patient(db: DbSession, user_id: uuid.UUID, patient_id: uuid.UUID, role: str) -> str:
    patient = await db.get(Patient, patient_id)
    if patient is None or patient.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
    return await require_app_role(db, user_id, role, patient.course_id)


@router.get("", response_model=list[ClinicalNoteOut])
async def list_notes(
    user: CurrentUser,
    db: DbSession,
    patientId: uuid.UUID = Query(...),
    role: str = Query(...),
):
    role = await _require_role_for_patient(db, user.id, patientId, role)
    q = select(ClinicalNote).where(
        ClinicalNote.patient_id == patientId,
        ClinicalNote.archived.is_(False),
        ClinicalNote.deleted_at.is_(None),
    )
    if role == "student":
        q = q.where(ClinicalNote.author_id == user.id)
    notes = (await db.scalars(q.order_by(ClinicalNote.updated_at.desc()))).all()
    return [note_out(n) for n in notes]


@router.get("/review-queue", response_model=list[QueueItemOut])
async def review_queue(
    user: CurrentUser,
    db: DbSession,
    courseId: uuid.UUID = Query(...),
):
    notes = (
        await db.scalars(
            select(ClinicalNote).where(
                ClinicalNote.mode == "assessment",
                ClinicalNote.status != "draft",
                ClinicalNote.routed_to_id == user.id,
                ClinicalNote.archived.is_(False),
                ClinicalNote.deleted_at.is_(None),
            )
        )
    ).all()
    items: list[QueueItemOut] = []
    for n in notes:
        p = await db.get(Patient, n.patient_id)
        if p is None or p.course_id != courseId or p.deleted_at is not None:
            continue
        items.append(QueueItemOut(note=note_out(n), patient=patient_out(p)))
    items.sort(key=lambda i: i.note.signedAt or "", reverse=True)
    return items


@router.get("/{note_id}", response_model=ClinicalNoteOut)
async def get_note(note_id: uuid.UUID, user: CurrentUser, db: DbSession, role: str = Query(...)):
    n = await _get_note(db, note_id)
    role = await _require_role_for_patient(db, user.id, n.patient_id, role)
    if role == "student" and n.author_id != user.id:
        await log_event(
            db, action="note.view", entity_type="note", actor_user_id=user.id,
            entity_id=str(note_id), details={"result": "denied"},
        )
        await db.commit()
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You can only open notes you wrote.")
    await log_event(
        db, action="note.view", entity_type="note", actor_user_id=user.id,
        entity_id=str(note_id), details={"result": "ok"},
    )
    await db.commit()
    return note_out(n)


@router.post("", response_model=ClinicalNoteOut, status_code=status.HTTP_201_CREATED)
async def create_draft(body: CreateNoteIn, user: CurrentUser, db: DbSession):
    try:
        patient_id = uuid.UUID(body.patientId)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid patient id")
    patient = await db.get(Patient, patient_id)
    if patient is None or patient.deleted_at is not None:
        raise HTTPException(status_code=404, detail="Patient not found")

    enc = patient.encounter or {}
    note = ClinicalNote(
        patient_id=patient.id,
        encounter_id=str(enc.get("id") or f"enc_{patient.id}"),
        template_id=body.templateId,
        author_id=user.id,
        author_name=user.full_name,
        author_discipline=body.discipline,
        mode=patient.mode,
        status="draft",
        version=1,
        content={},
        diagnoses=[],
        feedback=[],
        addenda=[],
    )
    db.add(note)
    await log_event(
        db, action="note.create", entity_type="note", actor_user_id=user.id, entity_id="pending",
    )
    await db.commit()
    await db.refresh(note)
    # Fix entity_id after flush — re-log is noisy; entity id is on the row now.
    return note_out(note)


@router.patch("/{note_id}", response_model=ClinicalNoteOut)
async def save_draft(note_id: uuid.UUID, body: DraftPatchIn, user: CurrentUser, db: DbSession):
    n = await _get_note(db, note_id)
    if n.author_id != user.id:
        raise HTTPException(status_code=403, detail="Only the author can edit this note.")
    if n.status not in ("draft", "returned"):
        raise HTTPException(status_code=409, detail="This note is signed. Add an addendum instead.")
    if n.version != body.expectedVersion:
        raise HTTPException(
            status_code=409,
            detail="This note was changed in another window. Reload to see the latest version before editing.",
        )
    if body.templateId is not None:
        n.template_id = body.templateId
    if body.content is not None:
        n.content = body.content
    if body.diagnoses is not None:
        n.diagnoses = body.diagnoses
    if body.routedToId is not None:
        n.routed_to_id = uuid.UUID(body.routedToId) if body.routedToId else None
    n.version += 1
    await db.commit()
    await db.refresh(n)
    return note_out(n)


@router.post("/{note_id}/sign", response_model=ClinicalNoteOut)
async def sign_note(note_id: uuid.UUID, body: NoteActionIn, user: CurrentUser, db: DbSession):
    n = await _get_note(db, note_id)
    if n.author_id != user.id:
        raise HTTPException(status_code=403, detail="Only the author can sign this note.")
    if body.expectedVersion is not None and n.version != body.expectedVersion:
        raise HTTPException(status_code=409, detail="This note changed in another window. Reload and try again.")
    if n.mode == "assessment" and not n.routed_to_id:
        raise HTTPException(status_code=400, detail="Choose an instructor to review this note.")
    n.status = "pending_review" if n.mode == "assessment" else "signed"
    n.signed_at = _now()
    n.version += 1
    action = "note.sign_submit" if n.mode == "assessment" else "note.sign"
    await log_event(db, action=action, entity_type="note", actor_user_id=user.id, entity_id=str(note_id))
    await db.commit()
    await db.refresh(n)
    return note_out(n)


@router.post("/{note_id}/cosign", response_model=ClinicalNoteOut)
async def cosign_note(note_id: uuid.UUID, body: NoteActionIn, user: CurrentUser, db: DbSession):
    n = await _get_note(db, note_id)
    if not can_cosign(user):
        await log_event(
            db, action="note.cosign", entity_type="note", actor_user_id=user.id,
            entity_id=str(note_id), details={"result": "denied"},
        )
        await db.commit()
        raise HTTPException(status_code=403, detail="Your role can't co-sign notes.")
    if n.status != "pending_review":
        raise HTTPException(status_code=409, detail="Only notes pending review can be co-signed.")
    n.status = "cosigned"
    n.cosigned_at = _now()
    n.cosigned_by_name = user.full_name
    n.version += 1
    if body.comment and body.comment.strip():
        feedback = list(n.feedback or [])
        feedback.append({
            "id": f"c_{uuid.uuid4().hex[:8]}",
            "authorId": str(user.id),
            "authorName": user.full_name,
            "body": body.comment.strip(),
            "kind": "cosigned",
            "createdAt": _now().isoformat(),
        })
        n.feedback = feedback
    await log_event(db, action="note.cosign", entity_type="note", actor_user_id=user.id, entity_id=str(note_id))
    await db.commit()
    await db.refresh(n)
    return note_out(n)


@router.post("/{note_id}/return", response_model=ClinicalNoteOut)
async def return_note(note_id: uuid.UUID, body: NoteActionIn, user: CurrentUser, db: DbSession):
    n = await _get_note(db, note_id)
    if not can_cosign(user):
        raise HTTPException(status_code=403, detail="Your role can't return notes.")
    if not body.comment or not body.comment.strip():
        raise HTTPException(status_code=400, detail="Tell the student what to revise.")
    if n.status != "pending_review":
        raise HTTPException(status_code=409, detail="Only notes pending review can be returned.")
    n.status = "returned"
    n.version += 1
    feedback = list(n.feedback or [])
    feedback.append({
        "id": f"c_{uuid.uuid4().hex[:8]}",
        "authorId": str(user.id),
        "authorName": user.full_name,
        "body": body.comment.strip(),
        "kind": "returned",
        "createdAt": _now().isoformat(),
    })
    n.feedback = feedback
    await log_event(db, action="note.return", entity_type="note", actor_user_id=user.id, entity_id=str(note_id))
    await db.commit()
    await db.refresh(n)
    return note_out(n)


@router.post("/{note_id}/addendum", response_model=ClinicalNoteOut)
async def add_addendum(note_id: uuid.UUID, body: NoteActionIn, user: CurrentUser, db: DbSession):
    n = await _get_note(db, note_id)
    if n.status not in ("signed", "cosigned"):
        raise HTTPException(status_code=409, detail="Addenda are for signed notes. Edit the draft instead.")
    if not body.body or not body.body.strip():
        raise HTTPException(status_code=400, detail="Addendum body required")
    addenda = list(n.addenda or [])
    addenda.append({
        "id": f"ad_{uuid.uuid4().hex[:8]}",
        "authorName": user.full_name,
        "body": body.body.strip(),
        "createdAt": _now().isoformat(),
    })
    n.addenda = addenda
    n.version += 1
    await log_event(db, action="note.addendum", entity_type="note", actor_user_id=user.id, entity_id=str(note_id))
    await db.commit()
    await db.refresh(n)
    return note_out(n)
