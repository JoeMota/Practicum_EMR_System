import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession
from app.models.scheduling import Appointment, Referral
from app.schemas.clinical import AppointmentOut, ReferralIn, ReferralOut
from app.services.audit import log_event
from app.services.serializers import appointment_out, referral_out

router = APIRouter(tags=["scheduling"])


@router.get("/patients/{patient_id}/appointments", response_model=list[AppointmentOut])
async def list_appointments(patient_id: uuid.UUID, user: CurrentUser, db: DbSession):
    rows = (
        await db.scalars(select(Appointment).where(Appointment.patient_id == patient_id))
    ).all()
    return [appointment_out(a) for a in rows]


@router.get("/patients/{patient_id}/referrals", response_model=list[ReferralOut])
async def list_referrals(patient_id: uuid.UUID, user: CurrentUser, db: DbSession):
    rows = (await db.scalars(select(Referral).where(Referral.patient_id == patient_id))).all()
    return [referral_out(r) for r in rows]


@router.post("/referrals", response_model=ReferralOut, status_code=201)
async def create_referral(body: ReferralIn, user: CurrentUser, db: DbSession):
    try:
        pid = uuid.UUID(body.patientId)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid patient id")
    ref = Referral(
        patient_id=pid,
        to_discipline=body.toDiscipline,
        reason=body.reason,
        urgency=body.urgency,
        created_by_name=user.full_name,
        created_at=datetime.now(timezone.utc),
    )
    db.add(ref)
    await log_event(
        db,
        action="referral.create",
        entity_type="patient",
        actor_user_id=user.id,
        entity_id=str(pid),
        details={"to": body.toDiscipline},
    )
    await db.commit()
    await db.refresh(ref)
    return referral_out(ref)
