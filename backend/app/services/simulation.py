"""Shared simulation charts. Graded assessment copies stay private."""

import uuid
from datetime import date

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.clinical import (
    Allergy,
    Appointment,
    ChartSession,
    ClinicalNote,
    CourseMembership,
    Encounter,
    LabResult,
    Medication,
    Patient,
    Problem,
    SimulationAssignment,
)
from app.models.user import Role, User
from app.services.access import full_name, require
from app.services.audit import log_event
from app.services.charts import utcnow

CLINICIAN_STATIONS = ("pharmacist", "provider")


async def station_for(db: AsyncSession, patient_id: uuid.UUID, user_id: uuid.UUID) -> str | None:
    return await db.scalar(
        select(SimulationAssignment.station).where(
            SimulationAssignment.patient_id == patient_id,
            SimulationAssignment.user_id == user_id,
        )
    )


async def assigned_patient_ids(db: AsyncSession, user_id: uuid.UUID, course_id: uuid.UUID) -> set[uuid.UUID]:
    rows = await db.scalars(
        select(SimulationAssignment.patient_id)
        .join(Patient, Patient.id == SimulationAssignment.patient_id)
        .where(
            SimulationAssignment.user_id == user_id,
            Patient.course_id == course_id,
            Patient.deleted_at.is_(None),
        )
    )
    return set(rows.all())


async def stations_on(db: AsyncSession, patient_id: uuid.UUID) -> set[str]:
    rows = await db.scalars(
        select(SimulationAssignment.station).where(SimulationAssignment.patient_id == patient_id)
    )
    return set(rows.all())


def signer_required(stations: set[str]) -> str:
    if "provider" in stations:
        return "provider"
    return "pharmacist"


async def start_simulation(
    db: AsyncSession,
    *,
    source: Patient,
    actor: User,
    role: str,
    course_id: uuid.UUID,
    nurse_id: uuid.UUID,
    pharmacist_id: uuid.UUID | None,
    provider_id: uuid.UUID | None,
    ip: str | None,
) -> Patient:
    require(role, "case:author", "Your role can't start a simulation.")
    if source.mode != "case" or source.course_id != course_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Start a simulation from a case in this course.")
    if pharmacist_id is None and provider_id is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Assign a pharmacist or a provider.")
    seats = {"nurse": nurse_id, "pharmacist": pharmacist_id, "provider": provider_id}
    chosen: dict[uuid.UUID, str] = {}
    for station, user_id in seats.items():
        if user_id is None:
            continue
        if user_id in chosen:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Each station needs a different student.")
        chosen[user_id] = station
    for user_id in chosen:
        if not await _student_in_course(db, user_id, course_id):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Assign students who are on this course roster.")

    locks = dict(source.section_locks or {})
    locks["vitals"] = False
    clone = Patient(
        mrn=await _simulation_mrn(db),
        first_name=source.first_name,
        last_name=source.last_name,
        preferred_name=source.preferred_name,
        dob=source.dob,
        sex_at_birth=source.sex_at_birth,
        pronouns=source.pronouns,
        course_id=course_id,
        mode="simulation",
        simulation_phase="waiting_vitals",
        case_key=source.case_key,
        source_patient_id=source.id,
        owner_id=None,
        created_by_id=actor.id,
        chief_complaint=source.chief_complaint,
        hpi=source.hpi,
        lifecycle=source.lifecycle,
        encounter_status="Checked in",
        care_setting=source.care_setting,
        program=source.program,
        past_medical_history=source.past_medical_history,
        family_history=source.family_history,
        surgical_history=source.surgical_history,
        social_history=source.social_history,
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
        section_locks=locks,
        prefill_sections=[item for item in (source.prefill_sections or []) if item != "vitals"],
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
    db.add(clone)
    await db.flush()
    for user_id, station in chosen.items():
        db.add(SimulationAssignment(patient_id=clone.id, user_id=user_id, station=station))
    appointments = (await db.scalars(select(Appointment).where(Appointment.patient_id == source.id))).all()
    for item in appointments:
        db.add(Appointment(patient_id=clone.id, when=item.when, kind=item.kind, with_whom=item.with_whom))
    await log_event(
        db,
        action="simulation.start",
        entity_type="patient",
        entity_id=str(clone.id),
        actor_user_id=actor.id,
        course_id=course_id,
        ip_address=ip,
        detail=f"Started {clone.last_name}, {clone.first_name} ({clone.mrn})",
    )
    await db.flush()
    await db.refresh(
        clone,
        attribute_names=["allergies", "medications", "problems", "labs", "vitals", "lung_sounds", "encounter"],
    )
    return clone


async def end_simulation(db: AsyncSession, patient: Patient, actor: User, role: str, ip: str | None) -> None:
    require(role, "case:author", "Your role can't end a simulation.")
    if patient.mode != "simulation":
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Only a simulation chart can be ended this way.")
    patient.deleted_at = utcnow()
    await log_event(
        db,
        action="simulation.end",
        entity_type="patient",
        entity_id=str(patient.id),
        actor_user_id=actor.id,
        course_id=patient.course_id,
        ip_address=ip,
        detail=f"Ended {patient.last_name}, {patient.first_name} ({patient.mrn})",
    )


async def prepare_note(db: AsyncSession, patient: Patient, author: User, role: str, kind: str) -> str:
    if patient.mode != "simulation":
        return "visit"
    if role != "student":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Students assigned to the simulation write its notes.")
    station = await station_for(db, patient.id, author.id)
    if station is None:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You are not assigned to this simulation.")
    if kind == "clarification":
        if patient.simulation_phase != "closed":
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "A clarification opens only after the visit note is signed and closed.",
            )
        return "clarification"
    if patient.simulation_phase != "ready":
        raise HTTPException(status.HTTP_409_CONFLICT, "The chart is not ready. The nurse records vitals first.")
    if station not in CLINICIAN_STATIONS:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "The nurse records vitals. The pharmacist or provider writes the visit note.",
        )
    existing = await db.scalar(
        select(ClinicalNote.id).where(
            ClinicalNote.patient_id == patient.id,
            ClinicalNote.kind == "visit",
            ClinicalNote.archived.is_(False),
        )
    )
    if existing is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "This simulation already has a visit note.")
    return "visit"


async def may_edit_simulation_note(db: AsyncSession, note: ClinicalNote, author: User) -> bool:
    if note.mode != "simulation" or (note.kind or "visit") != "visit" or note.status not in {"draft", "returned"}:
        return False
    station = await station_for(db, note.patient_id, author.id)
    return station in CLINICIAN_STATIONS


async def sign_simulation(db: AsyncSession, note: ClinicalNote, author: User, patient: Patient) -> None:
    station = await station_for(db, patient.id, author.id)
    if (note.kind or "visit") == "clarification":
        if note.author_id != author.id:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Only the author can sign this clarification.")
        note.status = "signed"
        note.body_locked = True
        return
    required = signer_required(await stations_on(db, patient.id))
    if station != required:
        who = "provider" if required == "provider" else "pharmacist"
        raise HTTPException(status.HTTP_403_FORBIDDEN, f"The {who} signs this visit note and closes it.")
    if patient.simulation_phase != "ready":
        raise HTTPException(status.HTTP_409_CONFLICT, "Sign the visit note after vitals are recorded.")
    note.status = "signed"
    note.body_locked = True
    patient.simulation_phase = "closed"


async def presence_rows(db: AsyncSession, patient: Patient) -> list[dict]:
    sessions = (
        await db.scalars(
            select(ChartSession)
            .where(ChartSession.patient_id == patient.id)
            .order_by(ChartSession.last_seen_at.desc())
        )
    ).all()
    seen: set[uuid.UUID] = set()
    payload = []
    for row in sessions:
        if row.user_id in seen:
            continue
        seen.add(row.user_id)
        person = await db.get(User, row.user_id)
        if person is None:
            continue
        payload.append(
            {
                "user_id": str(person.id),
                "name": full_name(person),
                "station": await station_for(db, patient.id, person.id),
                "last_seen_at": row.last_seen_at,
            }
        )
    return payload


async def _student_in_course(db: AsyncSession, user_id: uuid.UUID, course_id: uuid.UUID) -> bool:
    found = await db.scalar(
        select(CourseMembership.id)
        .join(Role, CourseMembership.role_id == Role.id)
        .where(
            CourseMembership.user_id == user_id,
            CourseMembership.course_id == course_id,
            CourseMembership.deactivated_at.is_(None),
            Role.code == "student",
        )
    )
    return found is not None


async def _simulation_mrn(db: AsyncSession) -> str:
    count = await db.scalar(select(func.count()).select_from(Patient)) or 0
    for offset in range(50):
        candidate = f"SIM-{10000 + int(count) + offset}"
        exists = await db.scalar(select(Patient.id).where(Patient.mrn == candidate))
        if exists is None:
            return candidate
    raise HTTPException(status.HTTP_409_CONFLICT, "Couldn't allocate a simulation MRN. Try again.")
