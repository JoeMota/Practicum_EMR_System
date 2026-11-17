"""One answer key per case master. Students read it only after release and cosign."""

import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.clinical import CaseAnswerKey, ClinicalNote, Patient
from app.models.user import User
from app.schemas.clinical import AnswerKeyIn
from app.services.access import can, require_course
from app.services.audit import log_event


def can_read_answer_key(role: str) -> bool:
    return role == "admin" or can(role, "case:author") or can(role, "note:cosign")


async def student_may_read_answer_key(db: AsyncSession, *, patient: Patient, user: User) -> bool:
    """CASE-05 / REV-07: released timestamp on the copy + a cosigned note by this student."""
    if patient.answer_key_released_at is None:
        return False
    if patient.owner_id != user.id:
        return False
    note = await db.scalar(
        select(ClinicalNote.id).where(
            ClinicalNote.patient_id == patient.id,
            ClinicalNote.author_id == user.id,
            ClinicalNote.status == "cosigned",
            ClinicalNote.archived.is_(False),
        ).limit(1)
    )
    return note is not None


async def deny_answer_key(
    db: AsyncSession,
    *,
    user: User,
    role: str,
    rows,
    course_id: uuid.UUID,
    entity_id: str,
    ip: str | None,
    action: str,
    patient: Patient | None = None,
) -> None:
    require_course(role, course_id, user, rows)
    if action == "answer_key.update":
        allowed = can(role, "case:author")
    elif can_read_answer_key(role):
        allowed = True
    elif role == "student" and patient is not None:
        allowed = await student_may_read_answer_key(db, patient=patient, user=user)
    else:
        allowed = False
    if allowed:
        return
    await log_event(
        db,
        action="answer_key.view" if action != "answer_key.update" else action,
        entity_type="patient",
        entity_id=entity_id,
        actor_user_id=user.id,
        result="denied",
        course_id=course_id,
        ip_address=ip,
        detail="Role cannot view answer keys." if action != "answer_key.update" else "Role cannot edit answer keys.",
    )
    await db.commit()
    message = "Your role can't edit answer keys." if action == "answer_key.update" else "Your role can't view answer keys."
    raise HTTPException(status.HTTP_403_FORBIDDEN, message)


async def release_answer_key(db: AsyncSession, patient: Patient, actor: User) -> Patient:
    if patient.mode not in {"assessment", "simulation"}:
        raise HTTPException(status.HTTP_409_CONFLICT, "Release the answer key on a student's assigned chart.")
    if patient.source_patient_id is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "This chart has no case answer key to release.")
    master = await db.get(Patient, patient.source_patient_id)
    if master is None or master.mode != "case":
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Case answer key not found.")
    key = await db.scalar(select(CaseAnswerKey.id).where(CaseAnswerKey.patient_id == master.id))
    if key is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Write an answer key on the case before releasing it.")
    patient.answer_key_released_at = datetime.now(timezone.utc)
    await db.flush()
    return patient


async def read_answer_key(db: AsyncSession, patient: Patient) -> dict:
    row = await _row_for(db, patient)
    return _out(row)


async def upsert_answer_key(db: AsyncSession, patient: Patient, body: AnswerKeyIn, actor: User) -> dict:
    if patient.mode != "case":
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Answer keys belong to the case master.")
    diagnoses = _diagnoses(body)
    points = [point.strip() for point in body.plan_points if point.strip()]
    row = await db.scalar(select(CaseAnswerKey).where(CaseAnswerKey.patient_id == patient.id))
    if row is None:
        row = CaseAnswerKey(
            patient_id=patient.id,
            diagnoses=diagnoses,
            expected_cpt_codes=_expected_cpt_codes(body),
            plan_points=points,
            rationale=body.rationale.strip(),
            updated_by_id=actor.id,
        )
        db.add(row)
    else:
        row.diagnoses = diagnoses
        row.expected_cpt_codes = _expected_cpt_codes(body)
        row.plan_points = points
        row.rationale = body.rationale.strip()
        row.updated_by_id = actor.id
    await db.flush()
    await db.refresh(row)
    return _out(row)


async def _row_for(db: AsyncSession, patient: Patient) -> CaseAnswerKey | None:
    master_id = patient.id if patient.mode == "case" else patient.source_patient_id
    if master_id is None:
        return None
    if patient.mode != "case":
        master = await db.get(Patient, master_id)
        if master is None or master.mode != "case" or master.deleted_at is not None:
            return None
        master_id = master.id
    return await db.scalar(select(CaseAnswerKey).where(CaseAnswerKey.patient_id == master_id))


def _diagnoses(body: AnswerKeyIn) -> list[dict]:
    cleaned = []
    for item in body.diagnoses:
        code = item.code.strip()
        label = item.label.strip()
        if not code or not label:
            continue
        cleaned.append({
            "rank": len(cleaned) + 1,
            "code": code,
            "label": label,
            "rationale": item.rationale.strip(),
        })
    return cleaned


def _expected_cpt_codes(body: AnswerKeyIn) -> list[dict]:
    return [
        {"code": item.code.strip(), "label": item.label.strip()}
        for item in body.expected_cpt_codes
        if item.code.strip() and item.label.strip()
    ]


def _out(row: CaseAnswerKey | None) -> dict:
    if row is None:
        return {"diagnoses": [], "expected_cpt_codes": [], "plan_points": [], "rationale": ""}
    return {
        "diagnoses": list(row.diagnoses or []),
        "expected_cpt_codes": list(row.expected_cpt_codes or []),
        "plan_points": list(row.plan_points or []),
        "rationale": row.rationale or "",
        "updated_at": row.updated_at,
    }
