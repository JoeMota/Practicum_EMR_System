"""Authoring for case masters. Copies are separate rows and are never updated here."""

import copy
import uuid
from datetime import date

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.clinical_sections import LUNG_SOUND_FINDINGS, LUNG_SOUND_LOCATIONS, locks_or_default, prefill_or_default
from app.models.clinical import CaseAnswerKey, Course, Encounter, Patient
from app.models.user import User
from app.schemas.clinical import CaseIn
from app.services.audit import log_event
from app.services.charts import (
    CARE_SETTING,
    ENCOUNTER_STATUS,
    LIFECYCLE,
    _replace_children,
    load_patient,
    utcnow,
)

CODE_STATUS = {"Full code", "DNR", "DNI", "Other"}


async def list_cases(db: AsyncSession, course_id: uuid.UUID) -> list[Patient]:
    rows = await db.scalars(
        select(Patient)
        .where(
            Patient.course_id == course_id,
            Patient.mode == "case",
            Patient.deleted_at.is_(None),
        )
        .order_by(Patient.last_name, Patient.first_name)
    )
    return list(rows.all())


async def load_case(db: AsyncSession, case_id: uuid.UUID) -> Patient:
    patient = await load_patient(db, case_id)
    if patient.mode != "case":
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Case not found.")
    return patient


async def create_case(
    db: AsyncSession,
    *,
    body: CaseIn,
    actor: User,
    course_id: uuid.UUID,
    ip: str | None,
) -> Patient:
    _validate(body)
    patient = Patient(
        mrn=await _unique_case_mrn(db),
        first_name=body.first_name.strip(),
        last_name=body.last_name.strip(),
        preferred_name=(body.preferred_name or "").strip() or None,
        dob=body.dob,
        sex_at_birth=body.sex_at_birth.strip(),
        pronouns=(body.pronouns or "").strip() or None,
        course_id=course_id,
        mode="case",
        case_key=str(uuid.uuid4()),
        owner_id=None,
        created_by=actor,
        chief_complaint=body.chief_complaint.strip(),
        hpi=body.hpi.strip(),
        past_medical_history=body.past_medical_history.strip(),
        surgical_history=body.surgical_history.strip(),
        family_history=body.family_history.strip(),
        social_history=body.social_history.strip(),
        insurance_payer=(body.insurance_payer or "").strip() or None,
        insurance_member_id=(body.insurance_member_id or "").strip() or None,
        insurance_group_number=(body.insurance_group_number or "").strip() or None,
        insurance_notes=(body.insurance_notes or "").strip() or None,
        emergency_contact_name=(body.emergency_contact_name or "").strip() or None,
        emergency_contact_phone=(body.emergency_contact_phone or "").strip() or None,
        emergency_contact_relationship=(body.emergency_contact_relationship or "").strip() or None,
        code_status=_code_status(body.code_status),
        advance_directive_notes=(body.advance_directive_notes or "").strip() or None,
        hipaa_on_file=bool(body.hipaa_on_file),
        hipaa_signed_at=utcnow() if body.hipaa_on_file else None,
        hipaa_note=(body.hipaa_note or "").strip() or None,
        lifecycle=body.lifecycle,
        encounter_status=body.encounter_status,
        care_setting=body.care_setting,
        program=(body.program or "").strip() or None,
        is_training=True,
        section_locks=locks_or_default(body.section_locks),
        prefill_sections=prefill_or_default(body.prefill_sections),
        unit=(body.unit or "").strip() or None,
        room=(body.room or "").strip() or None,
        bed=(body.bed or "").strip() or None,
        encounter=Encounter(type=body.encounter_type.strip() or "Office visit", date=date.today()),
    )
    db.add(patient)
    await db.flush()
    await db.refresh(
        patient,
        attribute_names=["allergies", "medications", "problems", "labs", "vitals", "lung_sounds", "encounter"],
    )
    await _replace_children(db, patient, _children(body))
    patient.updated_at = utcnow()
    await log_event(
        db,
        action="case.create",
        entity_type="patient",
        entity_id=str(patient.id),
        actor_user_id=actor.id,
        course_id=course_id,
        ip_address=ip,
        detail=f"{patient.last_name}, {patient.first_name} ({patient.mrn})",
    )
    return await _reload(db, patient)


async def update_case(
    db: AsyncSession,
    *,
    patient: Patient,
    body: CaseIn,
    actor: User,
    ip: str | None,
) -> Patient:
    """Replace this master only. Rows with source_patient_id pointing here are left alone."""
    _validate(body)
    await db.refresh(
        patient,
        attribute_names=["allergies", "medications", "problems", "labs", "vitals", "lung_sounds", "encounter"],
    )
    patient.first_name = body.first_name.strip()
    patient.last_name = body.last_name.strip()
    patient.preferred_name = (body.preferred_name or "").strip() or None
    patient.dob = body.dob
    patient.sex_at_birth = body.sex_at_birth.strip()
    patient.pronouns = (body.pronouns or "").strip() or None
    patient.chief_complaint = body.chief_complaint.strip()
    patient.hpi = body.hpi.strip()
    patient.past_medical_history = body.past_medical_history.strip()
    patient.surgical_history = body.surgical_history.strip()
    patient.family_history = body.family_history.strip()
    patient.social_history = body.social_history.strip()
    patient.insurance_payer = (body.insurance_payer or "").strip() or None
    patient.insurance_member_id = (body.insurance_member_id or "").strip() or None
    patient.insurance_group_number = (body.insurance_group_number or "").strip() or None
    patient.insurance_notes = (body.insurance_notes or "").strip() or None
    patient.emergency_contact_name = (body.emergency_contact_name or "").strip() or None
    patient.emergency_contact_phone = (body.emergency_contact_phone or "").strip() or None
    patient.emergency_contact_relationship = (body.emergency_contact_relationship or "").strip() or None
    patient.code_status = _code_status(body.code_status)
    patient.advance_directive_notes = (body.advance_directive_notes or "").strip() or None
    patient.hipaa_note = (body.hipaa_note or "").strip() or None
    if body.hipaa_on_file and not patient.hipaa_on_file:
        patient.hipaa_signed_at = utcnow()
    elif not body.hipaa_on_file:
        patient.hipaa_signed_at = None
    patient.hipaa_on_file = bool(body.hipaa_on_file)
    patient.lifecycle = body.lifecycle
    patient.encounter_status = body.encounter_status
    patient.care_setting = body.care_setting
    patient.program = (body.program or "").strip() or None
    if patient.encounter is None:
        patient.encounter = Encounter(type=body.encounter_type.strip() or "Office visit", date=date.today())
    else:
        patient.encounter.type = body.encounter_type.strip() or "Office visit"
    if body.section_locks is not None:
        patient.section_locks = locks_or_default(body.section_locks)
    if body.prefill_sections is not None:
        patient.prefill_sections = prefill_or_default(body.prefill_sections)
    if "unit" in body.model_fields_set:
        patient.unit = (body.unit or "").strip() or None
    if "room" in body.model_fields_set:
        patient.room = (body.room or "").strip() or None
    if "bed" in body.model_fields_set:
        patient.bed = (body.bed or "").strip() or None
    await _replace_children(db, patient, _children(body))
    patient.updated_at = utcnow()
    await log_event(
        db,
        action="case.update",
        entity_type="patient",
        entity_id=str(patient.id),
        actor_user_id=actor.id,
        course_id=patient.course_id,
        ip_address=ip,
        detail=f"{patient.last_name}, {patient.first_name} ({patient.mrn})",
    )
    return await _reload(db, patient)


def _code_status(value: str | None) -> str | None:
    cleaned = (value or "").strip()
    return cleaned or None


def _validate(body: CaseIn) -> None:
    if not body.first_name.strip() or not body.last_name.strip():
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "First and last name are required.")
    if not body.sex_at_birth.strip():
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Sex at birth is required.")
    if body.lifecycle not in LIFECYCLE:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Unknown lifecycle status.")
    if body.encounter_status not in ENCOUNTER_STATUS:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Unknown encounter status.")
    if body.care_setting not in CARE_SETTING:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Unknown care setting.")
    status_value = _code_status(body.code_status)
    if status_value and status_value not in CODE_STATUS:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Unknown code status.")
    for lab in body.labs:
        if lab.name.strip() and lab.collected_at is None:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, f"Lab {lab.name} needs a collected date.")
    for row in body.lung_sounds:
        if not row.location.strip() and not row.finding.strip():
            continue
        location = row.location.strip().upper()
        finding = row.finding.strip().lower()
        if location not in LUNG_SOUND_LOCATIONS:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Unknown lung sound location.")
        if finding not in LUNG_SOUND_FINDINGS:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Unknown lung sound finding.")


def _children(body: CaseIn) -> dict:
    return {
        "allergies": [
            {
                "substance": row.substance.strip(),
                "reaction": _blank(row.reaction),
                "severity": _blank(row.severity),
                "category": row.category if row.category in {"medication", "food", "environmental"} else "medication",
            }
            for row in body.allergies
            if row.substance.strip()
        ],
        "medications": [
            {
                "name": row.name.strip(),
                "dose": row.dose.strip(),
                "route": row.route.strip(),
                "frequency": row.frequency.strip(),
                "indication": _blank(row.indication),
                "adherence": _blank(row.adherence),
                "access_cost": _blank(row.access_cost),
                "prescribed": row.prescribed,
                "is_compound": bool(row.is_compound),
                "compound_ingredients": _blank(row.compound_ingredients) if row.is_compound else None,
                "compound_vehicle": _blank(row.compound_vehicle) if row.is_compound else None,
                "compound_reason": _blank(row.compound_reason) if row.is_compound else None,
                "status": "active",
            }
            for row in body.medications
            if row.name.strip()
        ],
        "problems": [
            {"code": _blank(row.code), "description": row.description.strip(), "since": _blank(row.since)}
            for row in body.problems
            if row.description.strip()
        ],
        "labs": [
            {
                "name": row.name.strip(),
                "value": row.value.strip(),
                "unit": row.unit.strip(),
                "reference_range": row.reference_range.strip(),
                "flag": _blank(row.flag),
                "collected_at": row.collected_at.isoformat() if row.collected_at else None,
            }
            for row in body.labs
            if row.name.strip()
        ],
        "vitals": [
            {"label": row.label.strip(), "value": row.value.strip()}
            for row in body.vitals
            if row.label.strip()
        ],
        "lung_sounds": [
            {
                "location": row.location.strip().upper(),
                "finding": row.finding.strip().lower(),
                "notes": _blank(row.notes),
                "recorded_by_name": "Chart baseline",
                "status": "recorded",
            }
            for row in body.lung_sounds
            if row.location.strip() and row.finding.strip()
        ],
    }


def _blank(value: str | None) -> str | None:
    text = (value or "").strip()
    return text or None


async def _unique_case_mrn(db: AsyncSession) -> str:
    n = await db.scalar(select(func.count()).select_from(Patient).where(Patient.mrn.like("CASE-%"))) or 0
    for offset in range(50):
        candidate = f"CASE-{10001 + int(n) + offset}"
        exists = await db.scalar(select(Patient.id).where(Patient.mrn == candidate))
        if exists is None:
            return candidate
    raise HTTPException(status.HTTP_409_CONFLICT, "Couldn't allocate a unique MRN. Try again.")


def teaches_course(rows, course_id: uuid.UUID) -> bool:
    return any(
        row.course_id == course_id and row.role.code in {"instructor", "course_coordinator"}
        for row in rows
    )


async def grading_guide_for(db: AsyncSession, patient: Patient) -> dict:
    """Case guide when the master has one. Otherwise the course guide."""
    master = await _case_master(db, patient)
    guide = master.grading_guide if master is not None else None
    if guide and guide.get("criteria"):
        return {"file_name": guide.get("file_name"), "criteria": list(guide["criteria"]), "source": "case"}
    course = await db.get(Course, patient.course_id)
    course_guide = course.grading_guide if course is not None else None
    if course_guide and course_guide.get("criteria"):
        return {
            "file_name": course_guide.get("file_name"),
            "criteria": list(course_guide["criteria"]),
            "source": "course",
        }
    return {
        "file_name": course.rubric_file_name if course is not None else None,
        "criteria": [],
        "source": "course",
    }


async def save_case_rubric(db: AsyncSession, patient: Patient, filename: str, payload: bytes) -> dict:
    from app.services.rubric_import import guide_from_upload

    if patient.mode != "case":
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Rubrics belong to the case master.")
    if len(payload) > 8_000_000:
        raise HTTPException(status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, "Rubric files must be 8 MB or smaller.")
    guide = guide_from_upload(filename or "rubric.pdf", payload)
    patient.grading_guide = guide
    patient.updated_at = utcnow()
    return guide


async def deny_triggers(
    db: AsyncSession,
    *,
    user: User,
    role: str,
    rows,
    course_id: uuid.UUID,
    entity_id: str,
    ip: str | None,
) -> None:
    from app.services.access import require_course
    from app.services.answer_keys import can_read_answer_key

    require_course(role, course_id, user, rows)
    if can_read_answer_key(role):
        return
    await log_event(
        db,
        action="triggers.view",
        entity_type="patient",
        entity_id=entity_id,
        actor_user_id=user.id,
        result="denied",
        course_id=course_id,
        ip_address=ip,
        detail="Role cannot view planted triggers.",
    )
    await db.commit()
    raise HTTPException(status.HTTP_403_FORBIDDEN, "Your role can't view planted triggers.")


async def triggers_for(db: AsyncSession, patient: Patient) -> list[dict]:
    master = await _case_master(db, patient)
    if master is None:
        return []
    return [
        {"finding": item.get("finding", ""), "explanation": item.get("explanation", "")}
        for item in (master.planted_triggers or [])
        if isinstance(item, dict) and str(item.get("finding") or "").strip()
    ]


async def save_triggers(db: AsyncSession, patient: Patient, items: list) -> list[dict]:
    if patient.mode != "case":
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Triggers belong to the case master.")
    cleaned: list[dict] = []
    for item in items:
        finding = item.finding.strip()
        if not finding:
            continue
        cleaned.append({"finding": finding[:240], "explanation": item.explanation.strip()[:2000]})
    patient.planted_triggers = cleaned
    patient.updated_at = utcnow()
    return cleaned


async def copy_case(
    db: AsyncSession,
    *,
    patient: Patient,
    destination_id: uuid.UUID,
    actor: User,
    rows,
    ip: str | None,
) -> Patient:
    """New master in another course. Student charts, notes, and scores stay behind."""
    if destination_id == patient.course_id:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Pick a different course.")
    if not teaches_course(rows, destination_id):
        await log_event(
            db,
            action="case.copy",
            entity_type="patient",
            entity_id=str(patient.id),
            actor_user_id=actor.id,
            result="denied",
            course_id=destination_id,
            ip_address=ip,
            detail="Not an instructor in the destination course.",
        )
        await db.commit()
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You can only copy a case into a course you teach.")
    await ensure_destination_open(db, destination_id)
    await db.refresh(
        patient,
        attribute_names=["allergies", "medications", "problems", "labs", "vitals", "lung_sounds", "encounter"],
    )
    clone = Patient(
        mrn=await _unique_case_mrn(db),
        first_name=patient.first_name,
        last_name=patient.last_name,
        preferred_name=patient.preferred_name,
        dob=patient.dob,
        sex_at_birth=patient.sex_at_birth,
        pronouns=patient.pronouns,
        course_id=destination_id,
        mode="case",
        case_key=str(uuid.uuid4()),
        owner_id=None,
        created_by=actor,
        chief_complaint=patient.chief_complaint,
        hpi=patient.hpi,
        past_medical_history=patient.past_medical_history,
        surgical_history=patient.surgical_history,
        family_history=patient.family_history,
        social_history=patient.social_history,
        lifecycle=patient.lifecycle,
        encounter_status=patient.encounter_status,
        care_setting=patient.care_setting,
        program=patient.program,
        is_training=True,
        section_locks=dict(patient.section_locks or {}),
        prefill_sections=list(patient.prefill_sections or []),
        grading_guide=copy.deepcopy(patient.grading_guide) if patient.grading_guide else None,
        planted_triggers=copy.deepcopy(list(patient.planted_triggers or [])),
        unit=patient.unit,
        room=patient.room,
        bed=patient.bed,
        photo=patient.photo,
        photo_content_type=patient.photo_content_type,
        encounter=Encounter(
            type=patient.encounter.type if patient.encounter else "Office visit",
            date=date.today(),
        ),
    )
    db.add(clone)
    await db.flush()
    await _copy_children(db, patient, clone)
    key = await db.scalar(select(CaseAnswerKey).where(CaseAnswerKey.patient_id == patient.id))
    if key is not None:
        db.add(
            CaseAnswerKey(
                patient_id=clone.id,
                diagnoses=list(key.diagnoses or []),
                plan_points=list(key.plan_points or []),
                rationale=key.rationale or "",
                updated_by_id=actor.id,
            )
        )
    await log_event(
        db,
        action="case.copy",
        entity_type="patient",
        entity_id=str(clone.id),
        actor_user_id=actor.id,
        course_id=destination_id,
        ip_address=ip,
        detail=f"From {patient.mrn} into course {destination_id}",
    )
    return await _reload(db, clone)


async def _case_master(db: AsyncSession, patient: Patient) -> Patient | None:
    if patient.mode == "case":
        return patient
    if patient.source_patient_id is None:
        return None
    master = await db.get(Patient, patient.source_patient_id)
    if master is None or master.deleted_at is not None or master.mode != "case":
        return None
    return master


async def ensure_destination_open(db: AsyncSession, course_id: uuid.UUID) -> None:
    from app.services.access import ensure_course_open

    await ensure_course_open(db, course_id)


async def _copy_children(db: AsyncSession, source: Patient, clone: Patient) -> None:
    from app.models.clinical import Allergy, LabResult, LungSound, Medication, Problem, Vital

    for item in source.allergies:
        db.add(Allergy(
            patient_id=clone.id, substance=item.substance, reaction=item.reaction,
            severity=item.severity, category=item.category,
        ))
    for item in source.medications:
        db.add(Medication(
            patient_id=clone.id, name=item.name, dose=item.dose, route=item.route, frequency=item.frequency,
            indication=item.indication, adherence=item.adherence, access_cost=item.access_cost,
            status=item.status, prescribed=item.prescribed, discontinued_at=item.discontinued_at,
            is_compound=bool(item.is_compound),
            compound_ingredients=item.compound_ingredients,
            compound_vehicle=item.compound_vehicle,
            compound_reason=item.compound_reason,
            rxcui=item.rxcui, generic_name=item.generic_name, brand_names=list(item.brand_names or []),
            flags=list(item.flags or []),
        ))
    for item in source.problems:
        db.add(Problem(patient_id=clone.id, code=item.code, description=item.description, since=item.since))
    for item in source.labs:
        db.add(LabResult(
            patient_id=clone.id, name=item.name, value=item.value, unit=item.unit,
            reference_range=item.reference_range, flag=item.flag, collected_at=item.collected_at,
        ))
    for item in source.vitals:
        db.add(Vital(
            patient_id=clone.id, label=item.label, value=item.value,
            recorded_at=item.recorded_at, recorded_by_name=item.recorded_by_name, status=item.status or "recorded",
        ))
    for item in source.lung_sounds:
        db.add(LungSound(
            patient_id=clone.id, location=item.location, finding=item.finding, notes=item.notes,
            recorded_at=item.recorded_at, recorded_by_name=item.recorded_by_name, status=item.status or "recorded",
        ))


async def _reload(db: AsyncSession, patient: Patient) -> Patient:
    await db.flush()
    await db.refresh(
        patient,
        attribute_names=[
            "owner", "created_by", "allergies", "medications", "problems", "labs", "vitals", "lung_sounds", "encounter",
        ],
    )
    return patient
