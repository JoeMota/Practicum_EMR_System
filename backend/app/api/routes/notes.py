import uuid
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.api.deps import CurrentUser, DbSession
from app.core.config import settings
from app.models.clinical import ClinicalNote, Course, Patient
from app.schemas.clinical import (
    AddendumBody,
    CommentBody,
    DraftCreate,
    InstructorEdit,
    ScoreWrite,
    SectionCommentIn,
    DraftPatch,
    DoseCheckIn,
    DoseCheckOut,
    NoteOut,
    SuggestIn,
    QueueItemOut,
    SignRequest,
)
from app.services.access import ensure_course_open, may_read_note, memberships_for, require_course
from app.services.assist import suggest_section
from app.services.audit import log_event
from app.services.dose_check import check_text
from app.services.guardrails import guardrail_mode
from app.services.charts import ensure_visible, load_patient
from app.services.notes import (
    add_addendum,
    add_section_comment,
    cosign_note,
    create_draft,
    instructor_edit_note,
    save_scores,
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
    query = (
        select(ClinicalNote)
        .where(ClinicalNote.patient_id == patient.id, ClinicalNote.archived.is_(False))
        .options(selectinload(ClinicalNote.discipline))
    )
    if role == "student" and patient.mode != "simulation":
        query = query.where(ClinicalNote.author_id == user.id)
    notes = (await db.scalars(query.order_by(ClinicalNote.updated_at.desc()))).all()
    payload = []
    for note in notes:
        if not may_read_note(role, rows, patient.course_id, note):
            continue
        payload.append(note_out(await _reload(db, note), include_scores=role != "student"))
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
        kind=body.kind,
    )
    await db.commit()
    return note_out(await _reload(db, note), include_scores=role != "student")


@router.get("/notes/{note_id}", response_model=NoteOut, response_model_exclude_none=True)
async def get_note(
    note_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
    request: Request,
    role: Annotated[str, Query()],
):
    note = await load_note(db, note_id)
    await db.refresh(note, attribute_names=["discipline"])
    patient = await load_patient(db, note.patient_id)
    rows = await memberships_for(db, user.id)
    await ensure_visible(db, patient, user, role, rows, request_ip=_ip(request))
    if not may_read_note(role, rows, patient.course_id, note):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Note not found.")
    if role == "student" and note.author_id != user.id and patient.mode != "simulation":
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
    if note.sensitive or (note.sensitivity or "standard") != "standard":
        kind = note.sensitivity if note.sensitivity in {"psychiatry", "protected"} else "protected"
        await log_event(
            db,
            action="note.view_psychiatry" if kind == "psychiatry" else "note.view_sensitive",
            entity_type="note",
            entity_id=str(note.id),
            actor_user_id=user.id,
            course_id=patient.course_id,
            ip_address=_ip(request),
            details={"sensitivity": kind},
            detail=kind,
        )
        if kind == "psychiatry":
            await log_event(
                db,
                action="note.view_sensitive",
                entity_type="note",
                entity_id=str(note.id),
                actor_user_id=user.id,
                course_id=patient.course_id,
                ip_address=_ip(request),
                details={"sensitivity": kind},
            )
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
    return note_out(await _reload(db, note), include_scores=role != "student")


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
    return note_out(await _reload(db, saved), include_scores=role != "student")


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
    return note_out(await _reload(db, signed), include_scores=role != "student")


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
    return note_out(await _reload(db, note), include_scores=role != "student")


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
    return note_out(await _reload(db, note), include_scores=role != "student")


@router.post("/notes/{note_id}/comments", response_model=NoteOut, response_model_exclude_none=True)
async def comment(
    note_id: uuid.UUID,
    body: SectionCommentIn,
    db: DbSession,
    user: CurrentUser,
    request: Request,
    role: Annotated[str, Query()],
):
    note = await _reviewable(db, user, role, note_id, request)
    patient = await load_patient(db, note.patient_id)
    await ensure_course_open(db, patient.course_id)
    await add_section_comment(db, note, user, role, body.section_id, body.body, _ip(request), patient.course_id)
    await db.commit()
    return note_out(await _reload(db, note), include_scores=role != "student")


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
    return note_out(await _reload(db, note), include_scores=role != "student")


@router.patch("/notes/{note_id}/instructor-edit", response_model=NoteOut, response_model_exclude_none=True)
async def instructor_edit(
    note_id: uuid.UUID,
    body: InstructorEdit,
    db: DbSession,
    user: CurrentUser,
    request: Request,
    role: Annotated[str, Query()],
):
    note = await _reviewable(db, user, role, note_id, request)
    patient = await load_patient(db, note.patient_id)
    await ensure_course_open(db, patient.course_id)
    await instructor_edit_note(db, note, user, role, body.model_dump(exclude_unset=True), _ip(request), patient.course_id)
    await db.commit()
    return note_out(await _reload(db, note), include_scores=True)


@router.put("/notes/{note_id}/scores", response_model=NoteOut, response_model_exclude_none=True)
async def put_scores(
    note_id: uuid.UUID,
    body: ScoreWrite,
    db: DbSession,
    user: CurrentUser,
    request: Request,
    role: Annotated[str, Query()],
):
    note = await _reviewable(db, user, role, note_id, request)
    patient = await load_patient(db, note.patient_id)
    await ensure_course_open(db, patient.course_id)
    await save_scores(db, note, user, role, body.model_dump(), _ip(request), patient.course_id)
    await db.commit()
    return note_out(await _reload(db, note), include_scores=True)


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
            .options(selectinload(ClinicalNote.discipline))
            .order_by(ClinicalNote.updated_at.desc())
        )
    ).all()
    items = []
    for note in notes:
        if not may_read_note(role, rows, course_id, note):
            continue
        patient = await load_patient(db, note.patient_id)
        owner = f"{patient.owner.first_name} {patient.owner.last_name}" if patient.owner else None
        items.append({"note": note_out(await _reload(db, note), include_scores=role != "student"), "patient": patient_out(patient, owner_name=owner, viewer_role=role)})
    return items


async def _reviewable(db, user, role: str, note_id: uuid.UUID, request: Request) -> ClinicalNote:
    note = await load_note(db, note_id)
    await db.refresh(note, attribute_names=["discipline"])
    patient = await load_patient(db, note.patient_id)
    rows = await memberships_for(db, user.id)
    await ensure_visible(db, patient, user, role, rows, request_ip=_ip(request))
    if not may_read_note(role, rows, patient.course_id, note):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Note not found.")
    return note


@router.post("/notes/{note_id}/suggest")
async def suggest_note(
    note_id: uuid.UUID,
    body: SuggestIn,
    db: DbSession,
    user: CurrentUser,
    request: Request,
    role: Annotated[str, Query()],
):
    note = await load_note(db, note_id)
    await db.refresh(note, attribute_names=["discipline"])
    if note.sensitive or (note.sensitivity or "standard") != "standard":
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Note not found.")
    patient = await load_patient(db, note.patient_id)
    rows = await memberships_for(db, user.id)
    await ensure_visible(db, patient, user, role, rows, request_ip=_ip(request))
    ensure_can_read(note, user, role)
    course = await db.get(Course, patient.course_id)
    if course is None or not course.ai_assist or not (settings.AI_API_URL or "").strip():
        raise HTTPException(status.HTTP_409_CONFLICT, "Assist is off.")
    context = "\n".join(
        part
        for part in (
            patient.chief_complaint,
            patient.hpi,
            "; ".join(f"{item.name} {item.dose}" for item in patient.medications if item.status == "active"),
        )
        if part
    )
    suggestion = await suggest_section(body.section_id, context)
    await log_event(
        db,
        action="ai.suggest",
        entity_type="note",
        entity_id=str(note.id),
        actor_user_id=user.id,
        course_id=patient.course_id,
        ip_address=_ip(request),
        details={"section": body.section_id, "model": settings.AI_MODEL},
    )
    await db.commit()
    return {"sectionId": body.section_id, "suggestion": suggestion}


@router.post("/notes/{note_id}/dose-check", response_model=DoseCheckOut)
async def dose_check_note(
    note_id: uuid.UUID,
    body: DoseCheckIn,
    db: DbSession,
    user: CurrentUser,
    request: Request,
    role: Annotated[str, Query()],
):
    note = await load_note(db, note_id)
    await db.refresh(note, attribute_names=["discipline"])
    patient = await load_patient(db, note.patient_id)
    rows = await memberships_for(db, user.id)
    await ensure_visible(db, patient, user, role, rows, request_ip=_ip(request))
    if not may_read_note(role, rows, patient.course_id, note):
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Note not found.")
    names = [item.name for item in patient.medications if item.status != "discontinued"]
    flags = check_text(body.text, names)
    mode = await guardrail_mode(db, patient.course_id)
    if role != "student" or mode == "off" or not flags:
        return {"flags": [], "blocked": False, "needs_acknowledgement": False}
    acknowledged = set(body.acknowledged_flags)
    missing = any(flag["code"] not in acknowledged for flag in flags)
    return {
        "flags": flags,
        "blocked": mode == "block",
        "needs_acknowledgement": mode == "acknowledge" and missing,
    }
