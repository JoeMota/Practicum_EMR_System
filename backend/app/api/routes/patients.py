import uuid
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Request, status
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession
from app.models.clinical import ClinicalNote, Patient
from app.models.user import User
from app.schemas.clinical import AssignCase, PatientOut, PatientRowOut, StatusPatch
from app.services.access import ensure_course_open, memberships_for, require_course
from app.services.audit import log_event
from app.services.charts import apply_status, assign_case, ensure_visible, load_patient, owner_name_for, reset_practice, unassign_case
from app.services.serialize import patient_out

router = APIRouter(prefix="/patients", tags=["patients"])


def _ip(request: Request) -> str | None:
    return request.client.host if request.client else None


@router.get("", response_model=list[PatientRowOut], response_model_exclude_none=True)
async def list_patients(
    db: DbSession,
    user: CurrentUser,
    request: Request,
    course_id: Annotated[uuid.UUID, Query()],
    role: Annotated[str, Query()],
):
    rows = await memberships_for(db, user.id)
    from app.services.access import require_course

    require_course(role, course_id, user, rows)
    patients = list(
        (
            await db.scalars(
                select(Patient).where(Patient.course_id == course_id, Patient.deleted_at.is_(None)).order_by(Patient.last_name)
            )
        ).all()
    )
    visible = []
    for patient in patients:
        if role == "student" and not (patient.mode == "practice" or patient.owner_id == user.id):
            continue
        if role not in {"student", "instructor", "admin", "front_desk"}:
            continue
        author_id = user.id if role == "student" else patient.owner_id
        note_query = select(ClinicalNote).where(ClinicalNote.patient_id == patient.id, ClinicalNote.archived.is_(False))
        if author_id is not None and role == "student":
            note_query = note_query.where(ClinicalNote.author_id == author_id)
        elif role != "student" and patient.owner_id is not None:
            note_query = note_query.where(ClinicalNote.author_id == patient.owner_id)
        latest = await db.scalar(note_query.order_by(ClinicalNote.updated_at.desc()))
        shown_owner = full_owner(patient)
        visible.append(
            {
                "patient": patient_out(patient, owner_name=owner_name_for(patient, role)),
                "owner_name": shown_owner,
                "latest_note": {"status": latest.status, "updated_at": latest.updated_at} if latest else None,
            }
        )
    return visible


@router.post("", response_model=PatientOut, response_model_exclude_none=True)
async def assign_patient(
    body: AssignCase,
    db: DbSession,
    user: CurrentUser,
    request: Request,
    course_id: Annotated[uuid.UUID, Query()],
    role: Annotated[str, Query()],
):
    rows = await memberships_for(db, user.id)
    require_course(role, course_id, user, rows)
    await ensure_course_open(db, course_id)
    source = await load_patient(db, body.source_patient_id)
    owner = await db.get(User, body.owner_id)
    if owner is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "That student isn't on the roster.")
    clone = await assign_case(
        db, source=source, owner=owner, actor=user, role=role, course_id=course_id, ip=_ip(request),
    )
    await db.commit()
    return patient_out(clone, owner_name=owner_name_for(clone, role))


def full_owner(patient: Patient) -> str | None:
    if patient.owner is None:
        return None
    return f"{patient.owner.first_name} {patient.owner.last_name}"


@router.get("/{patient_id}", response_model=PatientOut, response_model_exclude_none=True)
async def get_patient(
    patient_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
    request: Request,
    role: Annotated[str, Query()],
):
    patient = await load_patient(db, patient_id)
    rows = await memberships_for(db, user.id)
    await ensure_visible(db, patient, user, role, rows, request_ip=_ip(request))
    await log_event(
        db,
        action="chart.view",
        entity_type="patient",
        entity_id=str(patient.id),
        actor_user_id=user.id,
        course_id=patient.course_id,
        ip_address=_ip(request),
    )
    await db.commit()
    return patient_out(patient, owner_name=owner_name_for(patient, role))


@router.patch("/{patient_id}/status", response_model=PatientOut, response_model_exclude_none=True)
async def update_status(
    patient_id: uuid.UUID,
    body: StatusPatch,
    db: DbSession,
    user: CurrentUser,
    request: Request,
    role: Annotated[str, Query()],
):
    patient = await load_patient(db, patient_id)
    rows = await memberships_for(db, user.id)
    await ensure_visible(db, patient, user, role, rows, request_ip=_ip(request))
    await ensure_course_open(db, patient.course_id)
    await apply_status(db, patient, user, role, body.model_dump(exclude_unset=True), _ip(request))
    await db.commit()
    return patient_out(patient, owner_name=owner_name_for(patient, role))


@router.post("/{patient_id}/reset", status_code=204)
async def reset_patient(
    patient_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
    request: Request,
    role: Annotated[str, Query()],
):
    patient = await load_patient(db, patient_id)
    rows = await memberships_for(db, user.id)
    await ensure_visible(db, patient, user, role, rows, request_ip=_ip(request))
    await ensure_course_open(db, patient.course_id)
    await reset_practice(db, patient, user, role, _ip(request))
    await db.commit()


@router.delete("/{patient_id}", status_code=204)
async def unassign_patient(
    patient_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
    request: Request,
    role: Annotated[str, Query()],
):
    patient = await load_patient(db, patient_id)
    rows = await memberships_for(db, user.id)
    await ensure_visible(db, patient, user, role, rows, request_ip=_ip(request))
    await ensure_course_open(db, patient.course_id)
    await unassign_case(db, patient, user, role, _ip(request))
    await db.commit()
