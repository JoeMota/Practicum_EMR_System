import base64
import binascii
import uuid
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Request, status
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession
from app.models.clinical import ClinicalNote, Patient
from app.models.user import User
from app.models.clinical import MedicationAdministration, MedicationOrder
from app.schemas.clinical import (
    AdministerWrite,
    AdministrationReview,
    AllergyWrite,
    AnswerKeyOut,
    AssignCase,
    ChartPresence,
    HistoryWrite,
    LabWrite,
    MedicationOrderCreate,
    MedicationOrderOut,
    MedicationOrderReview,
    MedicationWrite,
    PatientOut,
    PatientRowOut,
    PhotoIn,
    PhotoOut,
    PlacementWrite,
    PresenceIn,
    ProblemWrite,
    StatusPatch,
    TriggersOut,
    LungSoundWrite,
    VitalWrite,
)
from app.schemas.intake import IntakeData, StaffIntakeOut
from app.services.chart_edits import (
    add_allergy,
    add_lab,
    add_lung_sound,
    add_medication,
    add_problem,
    add_vital,
    administer_medication,
    mark_lung_sound_entered_in_error,
    mark_vital_entered_in_error,
    delete_allergy,
    delete_medication,
    discontinue_medication,
    medication_order_out,
    record_presence,
    review_administration,
    review_medication_order,
    set_history,
    set_placement,
    submit_medication_order,
    update_allergy,
    update_medication,
)
from app.services.access import can, ensure_course_open, ensure_student_may_enter, may_read_note, memberships_for, require, require_course
from app.services.answer_keys import deny_answer_key, read_answer_key, release_answer_key
from app.services.cases import deny_triggers, grading_guide_for, triggers_for
from app.services.audit import log_event
from app.services.charts import apply_status, assign_case, ensure_visible, load_patient, owner_name_for, reset_practice, unassign_case
from app.services.intake import get_intake
from app.services.simulation import assigned_patient_ids, end_simulation, presence_rows, station_for
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
    await ensure_student_may_enter(db, role, course_id)
    sim_ids = await assigned_patient_ids(db, user.id, course_id) if role == "student" else set()
    patients = list(
        (
            await db.scalars(
                select(Patient).where(
                    Patient.course_id == course_id,
                    Patient.deleted_at.is_(None),
                    Patient.mode != "case",
                ).order_by(Patient.last_name)
            )
        ).all()
    )
    visible = []
    for patient in patients:
        if patient.mode == "simulation" and role == "front_desk":
            continue
        if role == "student" and patient.mode == "simulation":
            if patient.id not in sim_ids:
                continue
        elif role == "student" and not (patient.mode == "practice" or patient.owner_id == user.id):
            continue
        if role not in {"student", "instructor", "course_coordinator", "admin", "front_desk"}:
            continue
        note_query = select(ClinicalNote).where(ClinicalNote.patient_id == patient.id, ClinicalNote.archived.is_(False))
        if role == "student" and patient.mode != "simulation":
            note_query = note_query.where(ClinicalNote.author_id == user.id)
        elif role != "student" and patient.owner_id is not None and patient.mode != "simulation":
            note_query = note_query.where(ClinicalNote.author_id == patient.owner_id)
        if not can(role, "note:view_sensitive"):
            note_query = note_query.where(ClinicalNote.sensitive.is_(False))
        latest = await db.scalar(note_query.order_by(ClinicalNote.updated_at.desc()))
        if latest is not None and latest.sensitive:
            await db.refresh(latest, attribute_names=["discipline"])
            if not may_read_note(role, rows, course_id, latest):
                latest = await db.scalar(
                    note_query.where(ClinicalNote.sensitive.is_(False)).order_by(ClinicalNote.updated_at.desc())
                )
        shown_owner = full_owner(patient)
        open_flags = sum(1 for med in patient.medications if med.status == "active" and med.flags)
        station = await station_for(db, patient.id, user.id) if patient.mode == "simulation" else None
        visible.append(
            {
                "patient": patient_out(
                    patient,
                    owner_name=owner_name_for(patient, role),
                    viewer_role=role,
                    viewer_station=station,
                ),
                "owner_name": shown_owner,
                "latest_note": {"status": latest.status, "updated_at": latest.updated_at} if latest else None,
                "open_flag_count": open_flags,
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
    return patient_out(clone, owner_name=owner_name_for(clone, role), viewer_role=role)


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
    station = await station_for(db, patient.id, user.id) if patient.mode == "simulation" else None
    return patient_out(patient, owner_name=owner_name_for(patient, role), viewer_role=role, viewer_station=station)


@router.get("/{patient_id}/intake", response_model=StaffIntakeOut)
async def get_patient_intake(
    patient_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
    request: Request,
    role: Annotated[str, Query()],
):
    patient = await load_patient(db, patient_id)
    rows = await memberships_for(db, user.id)
    await ensure_visible(db, patient, user, role, rows, request_ip=_ip(request))
    intake = await get_intake(db, patient.id)
    return StaffIntakeOut(
        submitted=intake is not None,
        data=IntakeData.model_validate(intake.data) if intake is not None else None,
        updated_at=intake.updated_at if intake is not None else None,
    )


def _decode_photo(data: str) -> bytes:
    payload = data.split(",", 1)[1] if data.startswith("data:") else data
    try:
        raw = base64.b64decode(payload, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "The photo is not a valid image file.") from exc
    if len(raw) > 1_000_000:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "The photo must be 1 MB or smaller.")
    return raw


@router.get("/{patient_id}/photo", response_model=PhotoOut)
async def get_photo(
    patient_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
    request: Request,
    role: Annotated[str, Query()],
):
    patient = await load_patient(db, patient_id)
    rows = await memberships_for(db, user.id)
    await ensure_visible(db, patient, user, role, rows, request_ip=_ip(request))
    if not patient.photo:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "This chart has no photo.")
    return {"content_type": patient.photo_content_type or "image/jpeg", "data": base64.b64encode(patient.photo).decode()}


@router.put("/{patient_id}/photo", response_model=PhotoOut)
async def put_photo(
    patient_id: uuid.UUID,
    body: PhotoIn,
    db: DbSession,
    user: CurrentUser,
    request: Request,
    role: Annotated[str, Query()],
):
    patient = await load_patient(db, patient_id)
    rows = await memberships_for(db, user.id)
    require_course(role, patient.course_id, user, rows)
    require(role, "case:author", "Your role can't add a patient photo.")
    if patient.mode != "case":
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            "Add the photo on the case master. Assigned charts keep the photo from when they were assigned.",
        )
    raw = _decode_photo(body.data)
    patient.photo = raw
    patient.photo_content_type = body.content_type
    await log_event(
        db,
        action="patient.photo",
        entity_type="patient",
        entity_id=str(patient.id),
        actor_user_id=user.id,
        course_id=patient.course_id,
        ip_address=_ip(request),
    )
    await db.commit()
    return {"content_type": body.content_type, "data": base64.b64encode(raw).decode()}


@router.get("/{patient_id}/answer-key", response_model=AnswerKeyOut, response_model_exclude_none=True)
async def get_copy_answer_key(
    patient_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
    request: Request,
    role: Annotated[str, Query()],
):
    patient = await load_patient(db, patient_id)
    rows = await memberships_for(db, user.id)
    await deny_answer_key(
        db, user=user, role=role, rows=rows, course_id=patient.course_id,
        entity_id=str(patient.id), ip=_ip(request), action="answer_key.view", patient=patient,
    )
    payload = await read_answer_key(db, patient)
    await log_event(
        db, action="answer_key.view", entity_type="patient", entity_id=str(patient.id),
        actor_user_id=user.id, course_id=patient.course_id, ip_address=_ip(request),
    )
    await db.commit()
    return payload


@router.post("/{patient_id}/answer-key/release", response_model_exclude_none=True)
async def release_copy_answer_key(
    patient_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
    request: Request,
    role: Annotated[str, Query()],
):
    patient = await load_patient(db, patient_id)
    rows = await memberships_for(db, user.id)
    require_course(role, patient.course_id, user, rows)
    require(role, "note:cosign", "Only an instructor can release the answer key.")
    await release_answer_key(db, patient, user)
    await log_event(
        db,
        action="answer_key.release",
        entity_type="patient",
        entity_id=str(patient.id),
        actor_user_id=user.id,
        course_id=patient.course_id,
        ip_address=_ip(request),
    )
    await db.commit()
    return {
        "released": True,
        "answer_key_released_at": patient.answer_key_released_at,
    }


@router.get("/{patient_id}/grading-guide")
async def get_chart_grading_guide(
    patient_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
    request: Request,
    role: Annotated[str, Query()],
):
    patient = await load_patient(db, patient_id)
    rows = await memberships_for(db, user.id)
    await ensure_visible(db, patient, user, role, rows, request_ip=_ip(request))
    if role == "student":
        return {"file_name": None, "criteria": [], "source": "course"}
    return await grading_guide_for(db, patient)


@router.get("/{patient_id}/triggers", response_model=TriggersOut, response_model_exclude_none=True)
async def get_chart_triggers(
    patient_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
    request: Request,
    role: Annotated[str, Query()],
):
    patient = await load_patient(db, patient_id)
    rows = await memberships_for(db, user.id)
    await deny_triggers(
        db, user=user, role=role, rows=rows, course_id=patient.course_id,
        entity_id=str(patient.id), ip=_ip(request),
    )
    payload = await triggers_for(db, patient)
    await log_event(
        db, action="triggers.view", entity_type="patient", entity_id=str(patient.id),
        actor_user_id=user.id, course_id=patient.course_id, ip_address=_ip(request),
    )
    await db.commit()
    return {"triggers": payload}


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
    return patient_out(patient, owner_name=owner_name_for(patient, role), viewer_role=role)


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
    if patient.mode == "simulation":
        await end_simulation(db, patient, user, role, _ip(request))
    else:
        await unassign_case(db, patient, user, role, _ip(request))
    await db.commit()


async def _open_chart(patient_id, db, user, request, role):
    patient = await load_patient(db, patient_id)
    rows = await memberships_for(db, user.id)
    await ensure_visible(db, patient, user, role, rows, request_ip=_ip(request))
    await ensure_course_open(db, patient.course_id)
    return patient


@router.post("/{patient_id}/presence", status_code=204)
async def presence(
    patient_id: uuid.UUID,
    body: PresenceIn,
    db: DbSession,
    user: CurrentUser,
    request: Request,
    role: Annotated[str, Query()],
):
    patient = await load_patient(db, patient_id)
    rows = await memberships_for(db, user.id)
    await ensure_visible(db, patient, user, role, rows, request_ip=_ip(request))
    await record_presence(db, patient, user, _ip(request), active=body.active)
    await db.commit()


@router.get("/{patient_id}/opened", response_model=list[ChartPresence], response_model_exclude_none=True)
async def opened(
    patient_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
    request: Request,
    role: Annotated[str, Query()],
):
    patient = await load_patient(db, patient_id)
    rows = await memberships_for(db, user.id)
    await ensure_visible(db, patient, user, role, rows, request_ip=_ip(request))
    return await presence_rows(db, patient)


@router.post("/{patient_id}/allergies", response_model=PatientOut, response_model_exclude_none=True)
async def post_allergy(patient_id: uuid.UUID, body: AllergyWrite, db: DbSession, user: CurrentUser, request: Request, role: Annotated[str, Query()]):
    patient = await _open_chart(patient_id, db, user, request, role)
    await add_allergy(db, patient, user, role, body.model_dump(), _ip(request))
    await db.commit()
    return patient_out(await load_patient(db, patient.id), owner_name=owner_name_for(patient, role), viewer_role=role)


@router.patch("/{patient_id}/allergies/{allergy_id}", response_model=PatientOut, response_model_exclude_none=True)
async def patch_allergy(patient_id: uuid.UUID, allergy_id: uuid.UUID, body: AllergyWrite, db: DbSession, user: CurrentUser, request: Request, role: Annotated[str, Query()]):
    patient = await _open_chart(patient_id, db, user, request, role)
    await update_allergy(db, patient, user, role, allergy_id, body.model_dump(exclude_unset=True), _ip(request))
    await db.commit()
    return patient_out(await load_patient(db, patient.id), owner_name=owner_name_for(patient, role), viewer_role=role)


@router.delete("/{patient_id}/allergies/{allergy_id}", response_model=PatientOut, response_model_exclude_none=True)
async def remove_allergy(patient_id: uuid.UUID, allergy_id: uuid.UUID, db: DbSession, user: CurrentUser, request: Request, role: Annotated[str, Query()]):
    patient = await _open_chart(patient_id, db, user, request, role)
    await delete_allergy(db, patient, user, role, allergy_id, _ip(request))
    await db.commit()
    return patient_out(await load_patient(db, patient.id), owner_name=owner_name_for(patient, role), viewer_role=role)


@router.post("/{patient_id}/medications", response_model=PatientOut, response_model_exclude_none=True)
async def post_medication(patient_id: uuid.UUID, body: MedicationWrite, db: DbSession, user: CurrentUser, request: Request, role: Annotated[str, Query()]):
    patient = await _open_chart(patient_id, db, user, request, role)
    await add_medication(db, patient, user, role, body.model_dump(), _ip(request))
    await db.commit()
    return patient_out(await load_patient(db, patient.id), owner_name=owner_name_for(patient, role), viewer_role=role)


@router.patch("/{patient_id}/medications/{medication_id}", response_model=PatientOut, response_model_exclude_none=True)
async def patch_medication(patient_id: uuid.UUID, medication_id: uuid.UUID, body: MedicationWrite, db: DbSession, user: CurrentUser, request: Request, role: Annotated[str, Query()]):
    patient = await _open_chart(patient_id, db, user, request, role)
    await update_medication(db, patient, user, role, medication_id, body.model_dump(exclude_unset=True), _ip(request))
    await db.commit()
    return patient_out(await load_patient(db, patient.id), owner_name=owner_name_for(patient, role), viewer_role=role)


@router.post("/{patient_id}/medications/{medication_id}/discontinue", response_model=PatientOut, response_model_exclude_none=True)
async def discontinue(patient_id: uuid.UUID, medication_id: uuid.UUID, db: DbSession, user: CurrentUser, request: Request, role: Annotated[str, Query()]):
    patient = await _open_chart(patient_id, db, user, request, role)
    await discontinue_medication(db, patient, user, role, medication_id, _ip(request))
    await db.commit()
    return patient_out(await load_patient(db, patient.id), owner_name=owner_name_for(patient, role), viewer_role=role)


@router.delete("/{patient_id}/medications/{medication_id}", response_model=PatientOut, response_model_exclude_none=True)
async def remove_medication(
    patient_id: uuid.UUID,
    medication_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
    request: Request,
    role: Annotated[str, Query()],
    reason: Annotated[str | None, Query()] = None,
):
    patient = await _open_chart(patient_id, db, user, request, role)
    await delete_medication(db, patient, user, role, medication_id, reason, _ip(request))
    await db.commit()
    return patient_out(await load_patient(db, patient.id), owner_name=owner_name_for(patient, role), viewer_role=role)


@router.post("/{patient_id}/medications/{medication_id}/administrations", status_code=201)
async def administer(patient_id: uuid.UUID, medication_id: uuid.UUID, body: AdministerWrite, db: DbSession, user: CurrentUser, request: Request, role: Annotated[str, Query()]):
    patient = await _open_chart(patient_id, db, user, request, role)
    await administer_medication(db, patient, user, role, medication_id, body.dose_given, _ip(request))
    await db.commit()
    return {"status": "pending_review"}


@router.post("/{patient_id}/vitals", response_model=PatientOut, response_model_exclude_none=True)
async def post_vital(patient_id: uuid.UUID, body: VitalWrite, db: DbSession, user: CurrentUser, request: Request, role: Annotated[str, Query()]):
    patient = await _open_chart(patient_id, db, user, request, role)
    await add_vital(db, patient, user, role, body.model_dump(), _ip(request))
    await db.commit()
    return patient_out(await load_patient(db, patient.id), owner_name=owner_name_for(patient, role), viewer_role=role)


@router.post("/{patient_id}/vitals/{vital_id}/entered-in-error", response_model=PatientOut, response_model_exclude_none=True)
async def vital_entered_in_error(
    patient_id: uuid.UUID,
    vital_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
    request: Request,
    role: Annotated[str, Query()],
):
    patient = await _open_chart(patient_id, db, user, request, role)
    await mark_vital_entered_in_error(db, patient, user, role, vital_id, _ip(request))
    await db.commit()
    return patient_out(await load_patient(db, patient.id), owner_name=owner_name_for(patient, role), viewer_role=role)


@router.post("/{patient_id}/lung-sounds", response_model=PatientOut, response_model_exclude_none=True)
async def post_lung_sound(
    patient_id: uuid.UUID, body: LungSoundWrite, db: DbSession, user: CurrentUser, request: Request, role: Annotated[str, Query()]
):
    patient = await _open_chart(patient_id, db, user, request, role)
    await add_lung_sound(db, patient, user, role, body.model_dump(), _ip(request))
    await db.commit()
    return patient_out(await load_patient(db, patient.id), owner_name=owner_name_for(patient, role), viewer_role=role)


@router.post("/{patient_id}/lung-sounds/{lung_sound_id}/entered-in-error", response_model=PatientOut, response_model_exclude_none=True)
async def lung_sound_entered_in_error(
    patient_id: uuid.UUID,
    lung_sound_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
    request: Request,
    role: Annotated[str, Query()],
):
    patient = await _open_chart(patient_id, db, user, request, role)
    await mark_lung_sound_entered_in_error(db, patient, user, role, lung_sound_id, _ip(request))
    await db.commit()
    return patient_out(await load_patient(db, patient.id), owner_name=owner_name_for(patient, role), viewer_role=role)


@router.post("/{patient_id}/labs", response_model=PatientOut, response_model_exclude_none=True)
async def post_lab(patient_id: uuid.UUID, body: LabWrite, db: DbSession, user: CurrentUser, request: Request, role: Annotated[str, Query()]):
    patient = await _open_chart(patient_id, db, user, request, role)
    await add_lab(db, patient, user, role, body.model_dump(), _ip(request))
    await db.commit()
    return patient_out(await load_patient(db, patient.id), owner_name=owner_name_for(patient, role), viewer_role=role)


@router.post("/{patient_id}/problems", response_model=PatientOut, response_model_exclude_none=True)
async def post_problem(patient_id: uuid.UUID, body: ProblemWrite, db: DbSession, user: CurrentUser, request: Request, role: Annotated[str, Query()]):
    patient = await _open_chart(patient_id, db, user, request, role)
    await add_problem(db, patient, user, role, body.model_dump(), _ip(request))
    await db.commit()
    return patient_out(await load_patient(db, patient.id), owner_name=owner_name_for(patient, role), viewer_role=role)


@router.patch("/{patient_id}/history", response_model=PatientOut, response_model_exclude_none=True)
async def patch_history(patient_id: uuid.UUID, body: HistoryWrite, db: DbSession, user: CurrentUser, request: Request, role: Annotated[str, Query()]):
    patient = await _open_chart(patient_id, db, user, request, role)
    await set_history(db, patient, user, role, body.section, body.value, _ip(request))
    await db.commit()
    return patient_out(await load_patient(db, patient.id), owner_name=owner_name_for(patient, role), viewer_role=role)


@router.patch("/{patient_id}/placement", response_model=PatientOut, response_model_exclude_none=True)
async def patch_placement(patient_id: uuid.UUID, body: PlacementWrite, db: DbSession, user: CurrentUser, request: Request, role: Annotated[str, Query()]):
    patient = await _open_chart(patient_id, db, user, request, role)
    await set_placement(db, patient, user, role, body.model_dump(), _ip(request))
    await db.commit()
    return patient_out(await load_patient(db, patient.id), owner_name=owner_name_for(patient, role), viewer_role=role)


@router.get("/{patient_id}/administrations")
async def list_administrations(patient_id: uuid.UUID, db: DbSession, user: CurrentUser, request: Request, role: Annotated[str, Query()]):
    patient = await _open_chart(patient_id, db, user, request, role)
    rows = (
        await db.scalars(
            select(MedicationAdministration)
            .where(MedicationAdministration.patient_id == patient.id)
            .order_by(MedicationAdministration.administered_at.desc())
        )
    ).all()
    return [
        {
            "id": str(row.id),
            "medicationName": row.medication.name if row.medication else "",
            "doseGiven": row.dose_given,
            "studentName": row.student.full_name if row.student else "",
            "administeredAt": row.administered_at,
            "reviewStatus": row.review_status,
            "reviewComment": row.review_comment,
        }
        for row in rows
    ]


@router.post("/administrations/{administration_id}/review", status_code=204)
async def review_admin(
    administration_id: uuid.UUID,
    body: AdministrationReview,
    db: DbSession,
    user: CurrentUser,
    request: Request,
    role: Annotated[str, Query()],
):
    row = await db.get(MedicationAdministration, administration_id)
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Administration not found.")
    patient = await load_patient(db, row.patient_id)
    rows = await memberships_for(db, user.id)
    await ensure_visible(db, patient, user, role, rows, request_ip=_ip(request))
    await review_administration(db, row, user, role, body.decision, body.comment, _ip(request), patient.course_id)
    await db.commit()


@router.get("/{patient_id}/medication-orders", response_model=list[MedicationOrderOut], response_model_exclude_none=True)
async def list_medication_orders(patient_id: uuid.UUID, db: DbSession, user: CurrentUser, request: Request, role: Annotated[str, Query()]):
    patient = await _open_chart(patient_id, db, user, request, role)
    rows = (
        await db.scalars(
            select(MedicationOrder)
            .where(MedicationOrder.patient_id == patient.id)
            .order_by(MedicationOrder.submitted_at.desc())
        )
    ).all()
    return [medication_order_out(row) for row in rows]


@router.post("/{patient_id}/medication-orders", response_model=MedicationOrderOut, response_model_exclude_none=True)
async def post_medication_order(
    patient_id: uuid.UUID,
    body: MedicationOrderCreate,
    db: DbSession,
    user: CurrentUser,
    request: Request,
    role: Annotated[str, Query()],
):
    patient = await _open_chart(patient_id, db, user, request, role)
    order = await submit_medication_order(db, patient, user, role, body.medication_id, body.quantity, _ip(request))
    await db.commit()
    order = await db.get(MedicationOrder, order.id)
    return medication_order_out(order)


@router.post("/medication-orders/{order_id}/review", response_model=MedicationOrderOut, response_model_exclude_none=True)
async def review_medication_order_route(
    order_id: uuid.UUID,
    body: MedicationOrderReview,
    db: DbSession,
    user: CurrentUser,
    request: Request,
    role: Annotated[str, Query()],
):
    order = await db.get(MedicationOrder, order_id)
    if order is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Medication fill not found.")
    patient = await load_patient(db, order.patient_id)
    rows = await memberships_for(db, user.id)
    await ensure_visible(db, patient, user, role, rows, request_ip=_ip(request))
    await review_medication_order(db, order, user, role, body.decision, body.comment, _ip(request), patient)
    await db.commit()
    order = await db.get(MedicationOrder, order_id)
    return medication_order_out(order)
