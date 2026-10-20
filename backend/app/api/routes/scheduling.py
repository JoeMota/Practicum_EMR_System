import uuid
from typing import Annotated

from fastapi import APIRouter, Query, Request
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession
from app.models.clinical import Appointment, Referral
from app.models.user import Discipline
from app.schemas.clinical import AppointmentOut, ReferralCreate, ReferralOut
from app.services.access import ensure_course_open, memberships_for, require
from app.services.audit import log_event
from app.services.charts import ensure_visible, load_patient
from app.services.serialize import appointment_out, referral_out

router = APIRouter(tags=["scheduling"])


def _ip(request: Request) -> str | None:
    return request.client.host if request.client else None


@router.get("/patients/{patient_id}/appointments", response_model=list[AppointmentOut])
async def list_appointments(
    patient_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
    request: Request,
    role: Annotated[str, Query()],
):
    patient = await load_patient(db, patient_id)
    rows = await memberships_for(db, user.id)
    await ensure_visible(db, patient, user, role, rows, request_ip=_ip(request))
    items = (
        await db.scalars(select(Appointment).where(Appointment.patient_id == patient.id).order_by(Appointment.when))
    ).all()
    return [appointment_out(item) for item in items]


@router.get("/patients/{patient_id}/referrals", response_model=list[ReferralOut])
async def list_referrals(
    patient_id: uuid.UUID,
    db: DbSession,
    user: CurrentUser,
    request: Request,
    role: Annotated[str, Query()],
):
    patient = await load_patient(db, patient_id)
    rows = await memberships_for(db, user.id)
    await ensure_visible(db, patient, user, role, rows, request_ip=_ip(request))
    items = (await db.scalars(select(Referral).where(Referral.patient_id == patient.id))).all()
    return [referral_out(item) for item in items]


@router.post("/patients/{patient_id}/referrals", response_model=ReferralOut)
async def create_referral(
    patient_id: uuid.UUID,
    body: ReferralCreate,
    db: DbSession,
    user: CurrentUser,
    request: Request,
    role: Annotated[str, Query()],
):
    patient = await load_patient(db, patient_id)
    rows = await memberships_for(db, user.id)
    await ensure_visible(db, patient, user, role, rows, request_ip=_ip(request))
    await ensure_course_open(db, patient.course_id)
    require(role, "referral:create", "Your role can't create referrals.")
    discipline = await db.scalar(select(Discipline).where(Discipline.code == body.to_discipline))
    if discipline is None:
        from fastapi import HTTPException, status

        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Unknown discipline.")
    referral = Referral(
        patient_id=patient.id,
        to_discipline_id=discipline.id,
        reason=body.reason,
        urgency=body.urgency,
        created_by_id=user.id,
    )
    db.add(referral)
    await db.flush()
    await log_event(
        db,
        action="referral.create",
        entity_type="patient",
        entity_id=str(patient.id),
        actor_user_id=user.id,
        course_id=patient.course_id,
        ip_address=_ip(request),
        detail=f"to {body.to_discipline}",
    )
    await db.commit()
    stored = await db.get(Referral, referral.id)
    return referral_out(stored)

