import uuid

from fastapi import APIRouter, HTTPException, Query, status
from sqlalchemy import select

from app.api.deps import CurrentUser, DbSession
from app.models.note import ClinicalNote
from app.models.patient import Patient
from app.models.user import User
from app.schemas.clinical import PatientOut, PatientRowOut, PatientStatusIn
from app.services.access import can_reset_practice, require_app_role
from app.services.audit import log_event
from app.services.serializers import apply_patient_snapshot, patient_out

router = APIRouter(prefix="/patients", tags=["patients"])


def _visible(p: Patient, viewer: User, app_role: str) -> bool:
    if app_role == "student":
        return p.mode == "practice" or p.owner_id == viewer.id
    return app_role in ("instructor", "admin", "front_desk")


@router.get("", response_model=list[PatientRowOut])
async def list_patients(
    user: CurrentUser,
    db: DbSession,
    courseId: uuid.UUID = Query(...),
    role: str = Query(...),
):
    role = await require_app_role(db, user.id, role, courseId)

    patients = (
        await db.scalars(
            select(Patient).where(
                Patient.course_id == courseId,
                Patient.deleted_at.is_(None),
            )
        )
    ).all()

    owner_ids = [p.owner_id for p in patients if p.owner_id]
    owners = {}
    if owner_ids:
        for u in (await db.scalars(select(User).where(User.id.in_(owner_ids)))).all():
            owners[u.id] = u.full_name

    rows: list[PatientRowOut] = []
    for p in patients:
        if not _visible(p, user, role):
            continue
        author_id = user.id if role == "student" else p.owner_id
        note_q = select(ClinicalNote).where(
            ClinicalNote.patient_id == p.id,
            ClinicalNote.archived.is_(False),
            ClinicalNote.deleted_at.is_(None),
        )
        if author_id:
            note_q = note_q.where(ClinicalNote.author_id == author_id)
        notes = (await db.scalars(note_q.order_by(ClinicalNote.updated_at.desc()))).all()
        latest = notes[0] if notes else None
        rows.append(
            PatientRowOut(
                patient=patient_out(p, owners.get(p.owner_id) if p.owner_id else None),
                ownerName=owners.get(p.owner_id) if p.owner_id else None,
                latestNote=(
                    {"status": latest.status, "updatedAt": latest.updated_at.isoformat()}
                    if latest
                    else None
                ),
            )
        )
    return rows


@router.get("/{patient_id}", response_model=PatientOut)
async def get_patient(
    patient_id: uuid.UUID,
    user: CurrentUser,
    db: DbSession,
    role: str = Query(...),
):
    p = await db.get(Patient, patient_id)
    if p is None or p.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="This patient doesn't exist or was archived.")
    role = await require_app_role(db, user.id, role, p.course_id)
    if not _visible(p, user, role):
        await log_event(
            db,
            action="chart.view",
            entity_type="patient",
            actor_user_id=user.id,
            entity_id=str(patient_id),
            details={"result": "denied"},
        )
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This case belongs to another student. Each assessment case is private to the student it was assigned to.",
        )

    owner_name = None
    if role != "student" and p.owner_id:
        owner = await db.get(User, p.owner_id)
        owner_name = owner.full_name if owner else None

    await log_event(
        db,
        action="chart.view",
        entity_type="patient",
        actor_user_id=user.id,
        entity_id=str(patient_id),
        details={"result": "ok"},
    )
    await db.commit()
    return patient_out(p, owner_name)


@router.patch("/{patient_id}/status", response_model=PatientOut)
async def update_status(
    patient_id: uuid.UUID,
    body: PatientStatusIn,
    user: CurrentUser,
    db: DbSession,
    role: str = Query(...),
):
    p = await db.get(Patient, patient_id)
    if p is None or p.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found.")
    role = await require_app_role(db, user.id, role, p.course_id)

    patch = {k: v for k, v in body.model_dump().items() if v is not None}
    only_encounter = set(patch.keys()) <= {"encounter"}
    allowed = role in ("instructor", "admin") or (only_encounter and role in ("student", "instructor", "admin", "front_desk"))
    if not allowed:
        await log_event(
            db,
            action="patient.update_status",
            entity_type="patient",
            actor_user_id=user.id,
            entity_id=str(patient_id),
            details={"result": "denied"},
        )
        await db.commit()
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only instructors can change this status.")

    p.status = {**(p.status or {}), **patch}
    await log_event(
        db,
        action="patient.update_status",
        entity_type="patient",
        actor_user_id=user.id,
        entity_id=str(patient_id),
        details={"result": "ok", "patch": patch},
    )
    await db.commit()
    await db.refresh(p)
    return patient_out(p)


@router.post("/{patient_id}/reset", status_code=status.HTTP_204_NO_CONTENT)
async def reset_practice(patient_id: uuid.UUID, user: CurrentUser, db: DbSession):
    if not can_reset_practice(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only instructors can reset practice patients.")
    p = await db.get(Patient, patient_id)
    if p is None or p.mode != "practice" or not p.practice_snapshot:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only practice patients can be reset.")

    apply_patient_snapshot(p, p.practice_snapshot)
    notes = (
        await db.scalars(
            select(ClinicalNote).where(
                ClinicalNote.patient_id == patient_id,
                ClinicalNote.archived.is_(False),
            )
        )
    ).all()
    for n in notes:
        n.archived = True

    await log_event(
        db,
        action="patient.reset_practice",
        entity_type="patient",
        actor_user_id=user.id,
        entity_id=str(patient_id),
        details={"result": "ok", "archived_notes": len(notes)},
    )
    await db.commit()
