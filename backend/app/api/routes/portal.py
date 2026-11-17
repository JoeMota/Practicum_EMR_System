from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Request, status
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession
from app.models.clinical import ClinicalNote, Encounter, Patient
from app.schemas.intake import IntakeData, IntakeIdentity, PortalIntakeOut
from app.services.access import ensure_course_open, memberships_for, require, require_held_role
from app.services.audit import log_event
from app.services.charts import load_patient
from app.services.intake import defaults_from_patient, editability, get_intake, upsert_intake

router = APIRouter(prefix="/portal", tags=["portal"])


def _intake_out(patient: Patient, intake, editable: bool, reason: str | None) -> PortalIntakeOut:
    return PortalIntakeOut(
        data=IntakeData.model_validate(intake.data) if intake is not None else defaults_from_patient(patient),
        identity=IntakeIdentity(
            first_name=patient.first_name,
            last_name=patient.last_name,
            dob=patient.dob,
            sex_at_birth=patient.sex_at_birth,
            mrn=patient.mrn,
        ),
        source="patient" if intake is not None else "chart",
        updated_at=intake.updated_at if intake is not None else None,
        editable=editable,
        not_editable_reason=reason,
    )


@router.get("")
async def portal_chart(
    db: DbSession,
    user: CurrentUser,
    request: Request,
    role: Annotated[str, Query()] = "patient",
):
    rows = await memberships_for(db, user.id)
    require_held_role(user, "patient", rows)
    require(role, "portal:view", "The portal is view-only for patient accounts.")
    if user.portal_patient_id is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "This login is not linked to a chart.")
    patient = await load_patient(db, user.portal_patient_id)
    note = await db.scalar(
        select(ClinicalNote)
        .where(
            ClinicalNote.patient_id == patient.id,
            ClinicalNote.archived.is_(False),
            ClinicalNote.sensitive.is_(False),
            ClinicalNote.status.in_(("signed", "cosigned")),
        )
        .order_by(ClinicalNote.signed_at.desc())
    )
    summary = None
    visit = None
    if note is not None:
        parts = [f"{key}: {value}" for key, value in (note.content or {}).items() if str(value).strip()]
        summary = "\n".join(parts) if parts else None
        visit = await db.get(Encounter, note.encounter_id)
    if visit is None:
        visit = patient.encounter
    medications = [
        {
            "name": item.name,
            "dose": item.dose,
            "route": item.route,
            "frequency": item.frequency,
            "prescribed": item.prescribed,
        }
        for item in patient.medications
        if item.status == "active"
    ]
    labs = sorted(patient.labs, key=lambda lab: lab.name.casefold())
    labs.sort(key=lambda lab: lab.collected_at, reverse=True)
    result = {
        "patient": {
            "name": f"{patient.first_name} {patient.last_name}",
            "dob": patient.dob,
            "mrn": patient.mrn,
        },
        "labs": [
            {
                "name": lab.name,
                "value": lab.value,
                "unit": lab.unit,
                "reference_range": lab.reference_range,
                "flag": lab.flag,
                "collected_at": lab.collected_at,
            }
            for lab in labs
        ],
        "last_visit": {
            "date": note.signed_at.date().isoformat() if note is not None and note.signed_at else (visit.date if visit is not None else None),
            "type": visit.type if visit is not None else None,
            "summary": summary,
        },
        "insurance": {
            "payer": patient.insurance_payer,
            "member_id": patient.insurance_member_id,
            "group_number": patient.insurance_group_number,
        },
        "prescribed_medications": [item for item in medications if item["prescribed"]],
        "medication_list": medications,
    }
    await log_event(
        db,
        action="portal.view",
        entity_type="patient",
        entity_id=str(patient.id),
        actor_user_id=user.id,
        course_id=patient.course_id,
        ip_address=request.client.host if request.client else None,
    )
    await db.commit()
    return result


@router.get("/intake", response_model=PortalIntakeOut)
async def portal_intake(
    db: DbSession,
    user: CurrentUser,
    role: Annotated[str, Query()] = "patient",
):
    rows = await memberships_for(db, user.id)
    require_held_role(user, "patient", rows)
    require(role, "portal:view", "The portal is view-only for patient accounts.")
    if user.portal_patient_id is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "This login is not linked to a chart.")
    patient = await load_patient(db, user.portal_patient_id)
    intake = await get_intake(db, patient.id)
    editable, reason = await editability(db, patient)
    return _intake_out(patient, intake, editable, reason)


@router.put("/intake", response_model=PortalIntakeOut)
async def save_portal_intake(
    body: IntakeData,
    db: DbSession,
    user: CurrentUser,
    request: Request,
    role: Annotated[str, Query()] = "patient",
):
    rows = await memberships_for(db, user.id)
    require_held_role(user, "patient", rows)
    require(role, "portal:edit", "Your role can't edit portal information.")
    if user.portal_patient_id is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "This login is not linked to a chart.")
    patient = await load_patient(db, user.portal_patient_id)
    if patient.mode == "case":
        raise HTTPException(status.HTTP_409_CONFLICT, "Portal information is not available on case masters.")
    await ensure_course_open(db, patient.course_id)
    changed = await upsert_intake(db, patient, body, user)
    await log_event(
        db,
        action="portal.intake.update",
        entity_type="patient",
        entity_id=str(patient.id),
        actor_user_id=user.id,
        course_id=patient.course_id,
        ip_address=request.client.host if request.client else None,
        detail="Updated: " + ", ".join(changed),
    )
    await db.commit()
    intake = await get_intake(db, patient.id)
    editable, reason = await editability(db, patient)
    return _intake_out(patient, intake, editable, reason)
