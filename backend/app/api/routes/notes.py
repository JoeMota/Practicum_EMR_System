import uuid
from typing import Annotated

from fastapi import APIRouter, Query, Request
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession
from app.models.clinical import ClinicalNote, Patient
from app.schemas.clinical import (
    AddendumBody,
    CommentBody,
    DraftCreate,
    DraftPatch,
    NoteOut,
    QueueItemOut,
    SignRequest,
)
from app.services.access import ensure_course_open, memberships_for, require_course
from app.services.audit import log_event
from app.services.charts import ensure_visible, load_patient
from app.services.notes import (
    add_addendum,
    cosign_note,
    create_draft,
    ensure_can_read,
    load_note,
    return_note,
    save_draft,
    sign_note,
)
from app.services.serialize import note_out, patient_out

router = APIRouter(tags=["notes"])


def _ip(request: Request) -> str | None:
    return request.client.host if request.client else None


async def _reload(db, note: ClinicalNote) -> ClinicalNote:
    note_id = note.id
    await db.flush()
    db.expire(note)
    loaded = await load_note(db, note_id)
    await db.refresh(loaded, attribute_names=["author", "discipline", "cosigned_by", "feedback", "addenda"])
    for item in loaded.feedback:
        await db.refresh(item, attribute_names=["author"])
    for item in loaded.addenda:
        await db.refresh(item, attribute_names=["author"])
    return loaded


@router.get("/patients/{patient_id}/notes", response_model=list[NoteOut], response_model_exclude_none=True)
async def list_notes(
    patient_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
    request: Request,
    role: Annotated[str, Query()],
):
    patient = await load_patient(db, patient_id)
    rows = await memberships_for(db, user.id)
    await ensure_visible(db, patient, user, role, rows, request_ip=_ip(request))
    query = select(ClinicalNote).where(ClinicalNote.patient_id == patient.id, ClinicalNote.archived.is_(False))
    if role == "student":
        query = query.where(ClinicalNote.author_id == user.id)
    notes = (await db.scalars(query.order_by(ClinicalNote.updated_at.desc()))).all()
    payload = []
    for note in notes:
        payload.append(note_out(await _reload(db, note)))
    return payload


@router.post("/patients/{patient_id}/notes", response_model=NoteOut, response_model_exclude_none=True)
async def create_note(
    patient_id: uuid.UUID,
    body: DraftCreate,
    db: DbSession,
    user: CurrentUser,
    request: Request,
    role: Annotated[str, Query()],
):
    patient = await load_patient(db, patient_id)
    rows = await memberships_for(db, user.id)
    await ensure_visible(db, patient, user, role, rows, request_ip=_ip(request))
    await ensure_course_open(db, patient.course_id)
    note = await create_draft(
        db,
        author=user,
        patient=patient,
        template_id=body.template_id,
        discipline_code=body.discipline,
        role=role,
        ip=_ip(request),
    )
    await db.commit()
    return note_out(await _reload(db, note))


@router.get("/notes/{note_id}", response_model=NoteOut, response_model_exclude_none=True)
async def get_note(
    note_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
    request: Request,
    role: Annotated[str, Query()],
):
    note = await load_note(db, note_id)
    patient = await load_patient(db, note.patient_id)
    rows = await memberships_for(db, user.id)
    await ensure_visible(db, patient, user, role, rows, request_ip=_ip(request))
    if role == "student" and note.author_id != user.id:
        await log_event(
            db,
            action="note.view",
            entity_type="note",
            entity_id=str(note.id),
            actor_user_id=user.id,
            result="denied",
            course_id=patient.course_id,
            ip_address=_ip(request),
        )
        await db.commit()
    ensure_can_read(note, user, role)
    await db.refresh(note, attribute_names=["author", "discipline", "cosigned_by", "feedback", "addenda"])
    for item in note.feedback:
        await db.refresh(item, attribute_names=["author"])
    for item in note.addenda:
        await db.refresh(item, attribute_names=["author"])
    await log_event(
        db,
        action="note.view",
        entity_type="note",
        entity_id=str(note.id),
        actor_user_id=user.id,
        course_id=patient.course_id,
        ip_address=_ip(request),
    )
    await db.commit()
    return note_out(await _reload(db, note))


@router.patch("/notes/{note_id}", response_model=NoteOut, response_model_exclude_none=True)
async def patch_note(
    note_id: uuid.UUID,
    body: DraftPatch,
    db: DbSession,
    user: CurrentUser,
    request: Request,
    role: Annotated[str, Query()],
):
    note = await load_note(db, note_id)
    patient = await load_patient(db, note.patient_id)
    rows = await memberships_for(db, user.id)
    await ensure_visible(db, patient, user, role, rows, request_ip=_ip(request))
    await ensure_course_open(db, patient.course_id)
    data = body.model_dump(exclude_unset=True)
    saved = await save_draft(db, note, user, body.expected_version, data)
    await db.commit()
    return note_out(await _reload(db, saved))


@router.post("/notes/{note_id}/sign", response_model=NoteOut, response_model_exclude_none=True)
async def sign(
    note_id: uuid.UUID,
    body: SignRequest,
    db: DbSession,
    user: CurrentUser,
    request: Request,
    role: Annotated[str, Query()],
):
    note = await load_note(db, note_id)
    patient = await load_patient(db, note.patient_id)
    rows = await memberships_for(db, user.id)
    await ensure_visible(db, patient, user, role, rows, request_ip=_ip(request))
    await ensure_course_open(db, patient.course_id)
    signed = await sign_note(db, note, user, body.expected_version, _ip(request), patient.course_id)
    await db.commit()
    return note_out(await _reload(db, signed))


@router.post("/notes/{note_id}/cosign", response_model=NoteOut, response_model_exclude_none=True)
async def cosign(
    note_id: uuid.UUID,
    body: CommentBody,
    db: DbSession,
    user: CurrentUser,
    request: Request,
    role: Annotated[str, Query()],
):
    note = await _reviewable(db, user, role, note_id, request)
    patient = await load_patient(db, note.patient_id)
    await ensure_course_open(db, patient.course_id)
    await cosign_note(db, note, user, role, body.comment, _ip(request), patient.course_id)
    await db.commit()
    return note_out(await _reload(db, note))


@router.post("/notes/{note_id}/return", response_model=NoteOut, response_model_exclude_none=True)
async def return_for_revision(
    note_id: uuid.UUID,
    body: CommentBody,
    db: DbSession,
    user: CurrentUser,
    request: Request,
    role: Annotated[str, Query()],
):
    note = await _reviewable(db, user, role, note_id, request)
    patient = await load_patient(db, note.patient_id)
    await ensure_course_open(db, patient.course_id)
    await return_note(db, note, user, role, body.comment, _ip(request), patient.course_id)
    await db.commit()
    return note_out(await _reload(db, note))


@router.post("/notes/{note_id}/addenda", response_model=NoteOut, response_model_exclude_none=True)
async def addendum(
    note_id: uuid.UUID,
    body: AddendumBody,
    db: DbSession,
    user: CurrentUser,
    request: Request,
    role: Annotated[str, Query()],
):
    note = await load_note(db, note_id)
    patient = await load_patient(db, note.patient_id)
    rows = await memberships_for(db, user.id)
    await ensure_visible(db, patient, user, role, rows, request_ip=_ip(request))
    if role == "student" and note.author_id != user.id:
        ensure_can_read(note, user, role)
    await ensure_course_open(db, patient.course_id)
    await add_addendum(db, note, user, body.body, _ip(request), patient.course_id)
    await db.commit()
    return note_out(await _reload(db, note))


@router.get("/review-queue", response_model=list[QueueItemOut], response_model_exclude_none=True)
async def review_queue(
    db: DbSession,
    user: CurrentUser,
    course_id: Annotated[uuid.UUID, Query()],
    role: Annotated[str, Query()] = "instructor",
):
    rows = await memberships_for(db, user.id)
    require_course(role, course_id, user, rows)
    from app.services.access import require

    require(role, "note:cosign", "Your role can't review notes.")
    notes = (
        await db.scalars(
            select(ClinicalNote)
            .join(Patient, Patient.id == ClinicalNote.patient_id)
            .where(
                ClinicalNote.mode == "assessment",
                ClinicalNote.status.in_(("pending_review", "returned", "cosigned")),
                ClinicalNote.archived.is_(False),
                Patient.course_id == course_id,
                Patient.deleted_at.is_(None),
            )
            .order_by(ClinicalNote.updated_at.desc())
        )
    ).all()
    items = []
    for note in notes:
        patient = await load_patient(db, note.patient_id)
        owner = f"{patient.owner.first_name} {patient.owner.last_name}" if patient.owner else None
        items.append({"note": note_out(await _reload(db, note)), "patient": patient_out(patient, owner_name=owner)})
    return items


async def _reviewable(db, user, role: str, note_id: uuid.UUID, request: Request) -> ClinicalNote:
    note = await load_note(db, note_id)
    patient = await load_patient(db, note.patient_id)
    rows = await memberships_for(db, user.id)
    await ensure_visible(db, patient, user, role, rows, request_ip=_ip(request))
    return note
