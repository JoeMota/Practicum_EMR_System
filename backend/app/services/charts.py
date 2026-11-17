import uuid
from datetime import date, datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.clinical import (
    Allergy,
    Appointment,
    ClinicalNote,
    CourseMembership,
    Encounter,
    LabResult,
    LungSound,
    Medication,
    Patient,
    Problem,
    Vital,
)
from app.models.user import Role, User
from app.services.access import can, ensure_student_may_enter, full_name, require, require_course
from app.services.audit import log_event

LIFECYCLE = {"Active", "Inactive", "Prospective", "Discharged from practice", "Archived", "Deceased"}
ENCOUNTER_STATUS = {"Scheduled", "Checked in", "Roomed", "In progress", "Checked out", "Closed"}
CARE_SETTING = {"Outpatient", "Inpatient", "Emergency", "Discharged"}


async def load_patient(db: AsyncSession, patient_id: uuid.UUID) -> Patient:
    patient = await db.get(Patient, patient_id)
    if patient is None or patient.deleted_at is not None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "This patient doesn't exist or was archived.")
    return patient


async def ensure_visible(db: AsyncSession, patient: Patient, user: User, role: str, rows, *, request_ip: str | None) -> None:
    require_course(role, patient.course_id, user, rows)
    await ensure_student_may_enter(db, role, patient.course_id)
    if patient.mode == "case" and not can(role, "case:author"):
        await log_event(
            db,
            action="chart.view",
            entity_type="patient",
            entity_id=str(patient.id),
            actor_user_id=user.id,
            result="denied",
            course_id=patient.course_id,
            ip_address=request_ip,
            detail="Case master is hidden from this role.",
        )
        await db.commit()
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Case masters are only available to instructors.")
    if patient.mode == "simulation":
        from app.services.simulation import station_for

        if role == "front_desk":
            await log_event(
                db,
                action="chart.view",
                entity_type="patient",
                entity_id=str(patient.id),
                actor_user_id=user.id,
                result="denied",
                course_id=patient.course_id,
                ip_address=request_ip,
                detail="Front desk cannot open a simulation chart.",
            )
            await db.commit()
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Front desk can't open a simulation chart.")
        if role == "student" and await station_for(db, patient.id, user.id) is None:
            await log_event(
                db,
                action="chart.view",
                entity_type="patient",
                entity_id=str(patient.id),
                actor_user_id=user.id,
                result="denied",
                course_id=patient.course_id,
                ip_address=request_ip,
                detail="Simulation chart is limited to its assigned team.",
            )
            await db.commit()
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                "You are not assigned to this simulation. Graded charts stay private, and this live chart is only for its team.",
            )
    elif role == "student" and not (patient.mode == "practice" or patient.owner_id == user.id):
        await log_event(
            db,
            action="chart.view",
            entity_type="patient",
            entity_id=str(patient.id),
            actor_user_id=user.id,
            result="denied",
            course_id=patient.course_id,
            ip_address=request_ip,
            detail="Assessment case belongs to another student.",
        )
        await db.commit()
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "This case belongs to another student. Each assessment case is private to the student it was assigned to.",
        )
    if role not in {"student", "instructor", "course_coordinator", "admin", "front_desk"}:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Your role can't open charts.")


def owner_name_for(patient: Patient, role: str) -> str | None:
    if role == "student" or patient.owner is None:
        return None
    return full_name(patient.owner)


async def apply_status(db, patient: Patient, user: User, role: str, patch: dict, ip: str | None) -> None:
    provided = {key: value for key, value in patch.items() if value is not None}
    only_encounter = set(provided) <= {"encounter"}
    allowed = can_status(role, only_encounter)
    if not allowed:
        await log_event(
            db,
            action="patient.update_status",
            entity_type="patient",
            entity_id=str(patient.id),
            actor_user_id=user.id,
            result="denied",
            course_id=patient.course_id,
            ip_address=ip,
        )
        await db.commit()
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only instructors can change this status.")
    if "lifecycle" in provided and provided["lifecycle"] not in LIFECYCLE:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Unknown lifecycle status.")
    if "encounter" in provided and provided["encounter"] not in ENCOUNTER_STATUS:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Unknown encounter status.")
    if "care_setting" in provided and provided["care_setting"] not in CARE_SETTING:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Unknown care setting.")
    if "lifecycle" in provided:
        patient.lifecycle = provided["lifecycle"]
    if "encounter" in provided:
        patient.encounter_status = provided["encounter"]
    if "care_setting" in provided:
        patient.care_setting = provided["care_setting"]
    if "program" in provided:
        patient.program = provided["program"]
    await log_event(
        db,
        action="patient.update_status",
        entity_type="patient",
        entity_id=str(patient.id),
        actor_user_id=user.id,
        course_id=patient.course_id,
        ip_address=ip,
        detail=str(provided),
    )


def can_status(role: str, only_encounter: bool) -> bool:
    from app.services.access import can

    return can(role, "patient:update_status") or (only_encounter and can(role, "encounter:advance"))


async def reset_practice(db: AsyncSession, patient: Patient, user: User, role: str, ip: str | None) -> None:
    try:
        require(role, "patient:reset_practice", "Only instructors can reset practice patients.")
    except HTTPException:
        await log_event(
            db,
            action="patient.reset_practice",
            entity_type="patient",
            entity_id=str(patient.id),
            actor_user_id=user.id,
            result="denied",
            course_id=patient.course_id,
            ip_address=ip,
        )
        await db.commit()
        raise
    if patient.mode != "practice" or not patient.snapshot:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Only practice patients can be reset.")
    snap = patient.snapshot
    patient.chief_complaint = snap["chief_complaint"]
    patient.hpi = snap["hpi"]
    patient.lifecycle = snap["lifecycle"]
    patient.encounter_status = snap["encounter_status"]
    patient.care_setting = snap["care_setting"]
    patient.program = snap.get("program")
    patient.past_medical_history = snap.get("past_medical_history", "")
    patient.family_history = snap["family_history"]
    patient.surgical_history = snap["surgical_history"]
    patient.social_history = snap["social_history"]
    await _replace_children(db, patient, snap)
    if patient.encounter and snap.get("encounter"):
        patient.encounter.type = snap["encounter"]["type"]
        patient.encounter.date = date.fromisoformat(snap["encounter"]["date"])
    archived = await db.scalars(
        update(ClinicalNote)
        .where(ClinicalNote.patient_id == patient.id, ClinicalNote.archived.is_(False))
        .values(archived=True)
        .returning(ClinicalNote.id)
    )
    count = len(list(archived.all()))
    db.expire(patient, ["allergies", "medications", "problems", "labs", "vitals", "lung_sounds", "encounter"])
    await log_event(
        db,
        action="patient.reset_practice",
        entity_type="patient",
        entity_id=str(patient.id),
        actor_user_id=user.id,
        course_id=patient.course_id,
        ip_address=ip,
        detail=f"{count} notes archived",
    )


def _child_values(item: dict, fields: tuple[str, ...]) -> dict:
    values: dict = {}
    for field in fields:
        if field not in item or item[field] is None:
            continue
        value = item[field]
        if field == "collected_at" and isinstance(value, str):
            value = date.fromisoformat(value)
        elif field in {"recorded_at", "discontinued_at"} and isinstance(value, str):
            value = datetime.fromisoformat(value)
        values[field] = value
    return values


async def _replace_children(db: AsyncSession, patient: Patient, snap: dict) -> None:
    specs = (
        ("allergies", Allergy, ("substance", "reaction", "severity", "category")),
        (
            "medications",
            Medication,
            (
                "name",
                "dose",
                "route",
                "frequency",
                "indication",
                "adherence",
                "access_cost",
                "status",
                "prescribed",
                "is_compound",
                "compound_ingredients",
                "compound_vehicle",
                "compound_reason",
                "discontinued_at",
                "rxcui",
                "generic_name",
                "brand_names",
                "flags",
            ),
        ),
        ("problems", Problem, ("code", "description", "since")),
        ("labs", LabResult, ("name", "value", "unit", "reference_range", "flag", "collected_at")),
        ("vitals", Vital, ("label", "value", "recorded_at", "recorded_by_name", "status")),
        ("lung_sounds", LungSound, ("location", "finding", "notes", "recorded_at", "recorded_by_name", "status")),
    )
    for key, model, fields in specs:
        getattr(patient, key).clear()
    await db.flush()
    for key, model, fields in specs:
        for item in snap.get(key, []):
            getattr(patient, key).append(model(**_child_values(item, fields)))


def chart_snapshot(patient: Patient) -> dict:
    return {
        "chief_complaint": patient.chief_complaint,
        "hpi": patient.hpi,
        "lifecycle": patient.lifecycle,
        "encounter_status": patient.encounter_status,
        "care_setting": patient.care_setting,
        "program": patient.program,
        "past_medical_history": patient.past_medical_history,
        "family_history": patient.family_history,
        "surgical_history": patient.surgical_history,
        "social_history": patient.social_history,
        "section_locks": patient.section_locks,
        "prefill_sections": patient.prefill_sections,
        "unit": patient.unit,
        "room": patient.room,
        "bed": patient.bed,
        "encounter": {
            "type": patient.encounter.type,
            "date": patient.encounter.date.isoformat(),
        }
        if patient.encounter
        else None,
        "allergies": [
            {
                "id": str(a.id),
                "substance": a.substance,
                "reaction": a.reaction,
                "severity": a.severity,
                "category": a.category,
            }
            for a in patient.allergies
        ],
        "medications": [
            {
                "id": str(m.id),
                "name": m.name,
                "dose": m.dose,
                "route": m.route,
                "frequency": m.frequency,
                "indication": m.indication,
                "adherence": m.adherence,
                "access_cost": m.access_cost,
                "status": m.status,
                "prescribed": m.prescribed,
                "is_compound": bool(m.is_compound),
                "compound_ingredients": m.compound_ingredients,
                "compound_vehicle": m.compound_vehicle,
                "compound_reason": m.compound_reason,
                "discontinued_at": m.discontinued_at.isoformat() if m.discontinued_at else None,
                "rxcui": m.rxcui,
                "generic_name": m.generic_name,
                "brand_names": list(m.brand_names or []),
                "flags": list(m.flags or []),
            }
            for m in patient.medications
        ],
        "problems": [
            {"id": str(p.id), "code": p.code, "description": p.description, "since": p.since} for p in patient.problems
        ],
        "labs": [
            {
                "id": str(lab.id),
                "name": lab.name,
                "value": lab.value,
                "unit": lab.unit,
                "reference_range": lab.reference_range,
                "flag": lab.flag,
                "collected_at": lab.collected_at.isoformat(),
            }
            for lab in patient.labs
        ],
        "vitals": [
            {
                "id": str(v.id),
                "label": v.label,
                "value": v.value,
                "recorded_at": v.recorded_at.isoformat() if v.recorded_at else None,
                "recorded_by_name": v.recorded_by_name,
                "status": v.status or "recorded",
            }
            for v in patient.vitals
        ],
        "lung_sounds": [
            {
                "id": str(row.id),
                "location": row.location,
                "finding": row.finding,
                "notes": row.notes,
                "recorded_at": row.recorded_at.isoformat() if row.recorded_at else None,
                "recorded_by_name": row.recorded_by_name,
                "status": row.status or "recorded",
            }
            for row in patient.lung_sounds
        ],
    }


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


async def assign_case(
    db: AsyncSession,
    *,
    source: Patient,
    owner: User,
    actor: User,
    role: str,
    course_id: uuid.UUID,
    ip: str | None,
) -> Patient:
    require(role, "patient:create", "Your role can't assign cases.")
    if source.course_id != course_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "That chart isn't in this course.")
    if not await _student_in_course(db, owner.id, course_id):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Pick a student who is on this course roster.")
    already = await db.scalar(
        select(Patient).where(
            Patient.course_id == course_id,
            Patient.owner_id == owner.id,
            Patient.case_key == source.case_key,
            Patient.deleted_at.is_(None),
        )
    )
    if already is not None:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"{full_name(owner)} already has a copy of this case.",
        )

    clone = Patient(
        mrn=await _unique_mrn(db, owner),
        first_name=source.first_name,
        last_name=source.last_name,
        preferred_name=source.preferred_name,
        dob=source.dob,
        sex_at_birth=source.sex_at_birth,
        pronouns=source.pronouns,
        course_id=course_id,
        mode="assessment",
        case_key=source.case_key,
        source_patient_id=source.source_patient_id or source.id,
        owner_id=owner.id,
        chief_complaint=source.chief_complaint,
        hpi=source.hpi,
        lifecycle=source.lifecycle,
        encounter_status="Scheduled",
        care_setting=source.care_setting,
        program=source.program,
        past_medical_history=source.past_medical_history,
        family_history=source.family_history,
        surgical_history=source.surgical_history,
        social_history=source.social_history,
        snapshot=chart_snapshot(source),
        insurance_payer=source.insurance_payer,
        insurance_member_id=source.insurance_member_id,
        insurance_group_number=source.insurance_group_number,
        insurance_notes=source.insurance_notes,
        emergency_contact_name=source.emergency_contact_name,
        emergency_contact_phone=source.emergency_contact_phone,
        emergency_contact_relationship=source.emergency_contact_relationship,
        code_status=source.code_status,
        advance_directive_notes=source.advance_directive_notes,
        hipaa_on_file=bool(source.hipaa_on_file),
        hipaa_signed_at=source.hipaa_signed_at,
        hipaa_note=source.hipaa_note,
        is_training=True,
        section_locks=dict(source.section_locks or {}),
        prefill_sections=list(source.prefill_sections or []),
        unit=source.unit,
        room=source.room,
        bed=source.bed,
        photo=source.photo,
        photo_content_type=source.photo_content_type,
        encounter=Encounter(
            type=source.encounter.type if source.encounter else "Office visit",
            date=date.today(),
        ),
    )
    for item in source.allergies:
        clone.allergies.append(
            Allergy(substance=item.substance, reaction=item.reaction, severity=item.severity, category=item.category)
        )
    for item in source.medications:
        clone.medications.append(
            Medication(
                name=item.name, dose=item.dose, route=item.route, frequency=item.frequency,
                indication=item.indication, adherence=item.adherence, access_cost=item.access_cost,
                status=item.status, prescribed=item.prescribed, discontinued_at=item.discontinued_at,
                is_compound=bool(item.is_compound),
                compound_ingredients=item.compound_ingredients,
                compound_vehicle=item.compound_vehicle,
                compound_reason=item.compound_reason,
                rxcui=item.rxcui, generic_name=item.generic_name, brand_names=list(item.brand_names or []),
                flags=list(item.flags or []),
            )
        )
    for item in source.problems:
        clone.problems.append(Problem(code=item.code, description=item.description, since=item.since))
    for item in source.labs:
        clone.labs.append(
            LabResult(
                name=item.name, value=item.value, unit=item.unit, reference_range=item.reference_range,
                flag=item.flag, collected_at=item.collected_at,
            )
        )
    for item in source.vitals:
        clone.vitals.append(
            Vital(
                label=item.label,
                value=item.value,
                recorded_at=item.recorded_at,
                recorded_by_name=item.recorded_by_name,
                status=item.status or "recorded",
            )
        )
    for item in source.lung_sounds:
        clone.lung_sounds.append(
            LungSound(
                location=item.location,
                finding=item.finding,
                notes=item.notes,
                recorded_at=item.recorded_at,
                recorded_by_name=item.recorded_by_name,
                status=item.status or "recorded",
            )
        )
    db.add(clone)
    await db.flush()

    appointments = (await db.scalars(select(Appointment).where(Appointment.patient_id == source.id))).all()
    for item in appointments:
        db.add(Appointment(patient_id=clone.id, when=item.when, kind=item.kind, with_whom=item.with_whom))

    await log_event(
        db,
        action="patient.assign",
        entity_type="patient",
        entity_id=str(clone.id),
        actor_user_id=actor.id,
        course_id=course_id,
        ip_address=ip,
        detail=f"{full_name(owner)} received {clone.last_name}, {clone.first_name} ({clone.mrn})",
    )
    await db.refresh(
        clone,
        attribute_names=["owner", "allergies", "medications", "problems", "labs", "vitals", "lung_sounds", "encounter"],
    )
    return clone


async def unassign_case(db: AsyncSession, patient: Patient, actor: User, role: str, ip: str | None) -> None:
    require(role, "patient:create", "Your role can't unassign cases.")
    if patient.mode != "assessment" or patient.owner_id is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Only an assigned assessment copy can be removed from a student.")
    owner_name = full_name(patient.owner) if patient.owner else "the student"
    patient.deleted_at = utcnow()
    await log_event(
        db,
        action="patient.unassign",
        entity_type="patient",
        entity_id=str(patient.id),
        actor_user_id=actor.id,
        course_id=patient.course_id,
        ip_address=ip,
        detail=f"Removed {patient.last_name}, {patient.first_name} ({patient.mrn}) from {owner_name}",
    )


async def _student_in_course(db: AsyncSession, user_id: uuid.UUID, course_id: uuid.UUID) -> bool:
    row = await db.scalar(
        select(CourseMembership.id)
        .join(Role, CourseMembership.role_id == Role.id)
        .where(
            CourseMembership.user_id == user_id,
            CourseMembership.course_id == course_id,
            CourseMembership.deactivated_at.is_(None),
            Role.code == "student",
        )
    )
    return row is not None


async def _unique_mrn(db: AsyncSession, owner: User) -> str:
    initials = f"{owner.last_name[:1]}{owner.first_name[:1]}".upper() or "XX"
    n = await db.scalar(select(func.count()).select_from(Patient)) or 0
    for offset in range(50):
        candidate = f"TR-{10000 + int(n) + offset}-{initials}"
        exists = await db.scalar(select(Patient.id).where(Patient.mrn == candidate))
        if exists is None:
            return candidate
    raise HTTPException(status.HTTP_409_CONFLICT, "Couldn't allocate a unique MRN. Try again.")
