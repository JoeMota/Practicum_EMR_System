from datetime import date

from app.clinical_sections import locks_or_default, prefill_or_default
from app.core.config import settings
from app.models.clinical import (
    Appointment,
    ClinicalNote,
    Course,
    Patient,
    Referral,
)
from app.models.user import User
from app.services.access import full_name, memberships_for
from app.services.note_crypto import reveal_content, reveal_text
from app.services.sig import medication_sig


def _age(dob: date) -> int:
    today = date.today()
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))


def course_out(course: Course, instructor_ids: list[str]) -> dict:
    return {
        "id": str(course.id),
        "code": course.code,
        "title": course.title,
        "term": course.term,
        "status": course.status,
        "inactivity_days": course.inactivity_days,
        "instructor_ids": instructor_ids,
        "rubric_file_name": course.rubric_file_name,
        "grading_guide": course.grading_guide,
        "guardrail_profile": course.guardrail_profile or "practicum",
        "guardrail_mode": course.guardrail_mode,
        "ai_assist": bool(course.ai_assist),
        "ai_provider_configured": bool((settings.AI_API_URL or "").strip()),
    }


def patient_out(patient: Patient, *, owner_name: str | None, viewer_role: str | None = None, viewer_station: str | None = None) -> dict:
    encounter = patient.encounter
    payload = {
        "id": str(patient.id),
        "mrn": patient.mrn,
        "first_name": patient.first_name,
        "last_name": patient.last_name,
        "preferred_name": patient.preferred_name,
        "dob": patient.dob,
        "age_years": _age(patient.dob),
        "sex_at_birth": patient.sex_at_birth,
        "pronouns": patient.pronouns,
        "course_id": str(patient.course_id),
        "mode": patient.mode,
        "case_template_id": patient.case_key,
        "source_patient_id": str(patient.source_patient_id) if patient.source_patient_id else None,
        "owner_id": str(patient.owner_id) if patient.owner_id else None,
        "owner_name": owner_name,
        "is_training": True,
        "practice_label": patient.practice_label,
        "chief_complaint": patient.chief_complaint,
        "hpi": patient.hpi,
        "past_medical_history": patient.past_medical_history,
        "status": {
            "lifecycle": patient.lifecycle,
            "encounter": patient.encounter_status,
            "care_setting": patient.care_setting,
            "program": patient.program,
        },
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
                "sig": medication_sig(m.dose, m.route, m.frequency),
                "indication": m.indication,
                "adherence": m.adherence,
                "access_cost": m.access_cost,
                "status": m.status,
                "prescribed": m.prescribed,
                "is_compound": bool(m.is_compound),
                "compound_ingredients": m.compound_ingredients,
                "compound_vehicle": m.compound_vehicle,
                "compound_reason": m.compound_reason,
                "discontinued_at": m.discontinued_at,
                "rxcui": m.rxcui,
                "generic_name": m.generic_name,
                "brand_names": list(m.brand_names or []),
                "flags": list(m.flags or []),
            }
            for m in patient.medications
            if m.status != "entered_in_error"
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
                "collected_at": lab.collected_at,
            }
            for lab in patient.labs
        ],
        "vitals": [
            {
                "id": str(v.id),
                "label": v.label,
                "value": v.value,
                "recorded_at": v.recorded_at,
                "recorded_by_name": v.recorded_by_name,
                "status": v.status or "recorded",
            }
            for v in patient.vitals
            if viewer_role != "student" or (v.status or "recorded") != "entered_in_error"
        ],
        "lung_sounds": [
            {
                "id": str(row.id),
                "location": row.location,
                "finding": row.finding,
                "notes": row.notes,
                "recorded_at": row.recorded_at,
                "recorded_by_name": row.recorded_by_name,
                "status": row.status or "recorded",
            }
            for row in patient.lung_sounds
            if viewer_role != "student" or (row.status or "recorded") != "entered_in_error"
        ],
        "section_locks": locks_or_default(patient.section_locks),
        "prefill_sections": prefill_or_default(patient.prefill_sections),
        "unit": patient.unit,
        "room": patient.room,
        "bed": patient.bed,
        "has_photo": bool(patient.photo),
        "simulation_phase": patient.simulation_phase,
        "viewer_station": viewer_station,
        "family_history": patient.family_history,
        "surgical_history": patient.surgical_history,
        "social_history": patient.social_history,
        "encounter": {
            "id": str(encounter.id),
            "type": encounter.type,
            "date": encounter.date,
        }
        if encounter
        else None,
        "insurance": {
            "payer": patient.insurance_payer,
            "member_id": patient.insurance_member_id,
            "group_number": patient.insurance_group_number,
            "notes": patient.insurance_notes,
        },
        "emergency_contact": {
            "name": patient.emergency_contact_name,
            "phone": patient.emergency_contact_phone,
            "relationship": patient.emergency_contact_relationship,
        },
        "code_status": patient.code_status,
        "advance_directive_notes": patient.advance_directive_notes,
        "hipaa_on_file": bool(patient.hipaa_on_file),
        "hipaa_signed_at": patient.hipaa_signed_at,
        "hipaa_note": patient.hipaa_note,
    }
    return payload


def note_out(note: ClinicalNote, *, include_scores: bool = False) -> dict:
    payload = {
        "id": str(note.id),
        "patient_id": str(note.patient_id),
        "encounter_id": str(note.encounter_id),
        "template_id": note.template_id,
        "author_id": str(note.author_id),
        "author_name": full_name(note.author),
        "author_discipline": note.discipline.code,
        "mode": note.mode,
        "kind": note.kind or "visit",
        "status": note.status,
        "version": note.version,
        "content": reveal_content(note),
        "sensitivity": note.sensitivity or "standard",
        "diagnoses": note.diagnoses or [],
        "cpt_codes": note.cpt_codes or [],
        "body_locked": bool(note.body_locked),
        "routed_to_id": str(note.routed_to_id) if note.routed_to_id else None,
        "created_at": note.created_at,
        "updated_at": note.updated_at,
        "signed_at": note.signed_at,
        "cosigned_at": note.cosigned_at,
        "cosigned_by_name": full_name(note.cosigned_by) if note.cosigned_by else None,
        "feedback": [
            {
                "id": str(item.id),
                "author_id": str(item.author_id),
                "author_name": full_name(item.author),
                "body": reveal_text(item.body, item.body_cipher),
                "kind": item.kind,
                "section_id": item.section_id,
                "created_at": item.created_at,
            }
            for item in sorted(note.feedback, key=lambda item: item.created_at)
        ],
        "addenda": [
            {
                "id": str(item.id),
                "author_name": full_name(item.author),
                "body": reveal_text(item.body, item.body_cipher),
                "created_at": item.created_at,
            }
            for item in sorted(note.addenda, key=lambda item: item.created_at)
        ],
    }
    if include_scores:
        payload["rubric_scores"] = note.rubric_scores
    return payload


def authored_case_out(patient: Patient) -> dict:
    payload = patient_out(patient, owner_name=None)
    payload["created_by_name"] = full_name(patient.created_by) if patient.created_by else None
    payload["updated_at"] = patient.updated_at
    payload["grading_guide"] = patient.grading_guide
    payload["triggers"] = list(patient.planted_triggers or [])
    return payload


def appointment_out(row: Appointment) -> dict:
    return {"id": str(row.id), "patient_id": str(row.patient_id), "when": row.when, "kind": row.kind, "with_whom": row.with_whom}


def referral_out(row: Referral) -> dict:
    return {
        "id": str(row.id),
        "patient_id": str(row.patient_id),
        "to_discipline": row.to_discipline.code,
        "reason": row.reason,
        "urgency": row.urgency,
        "created_by_name": full_name(row.created_by),
        "created_at": row.created_at,
    }


async def user_out(db, user: User) -> dict:
    rows = await memberships_for(db, user.id)
    grouped: dict[tuple[str, str | None], list[str]] = {}
    for row in rows:
        key = (row.role.code, row.discipline.code if row.discipline else None)
        grouped.setdefault(key, []).append(str(row.course_id))
    roles = [
        {"role": role, "discipline": discipline, "course_ids": sorted(course_ids)}
        for (role, discipline), course_ids in sorted(grouped.items(), key=lambda item: (item[0][0], item[0][1] or ""))
    ]
    await db.refresh(user, attribute_names=["roles"])
    if any(item.code == "patient" for item in user.roles) and not any(item["role"] == "patient" for item in roles):
        roles.append({"role": "patient", "discipline": None, "course_ids": []})
    if any(item.code == "admin" for item in user.roles) and not any(item["role"] == "admin" for item in roles):
        from sqlalchemy import select

        from app.models.clinical import Course

        course_ids = [str(item) for item in (await db.scalars(select(Course.id))).all()]
        roles.append({"role": "admin", "discipline": None, "course_ids": sorted(course_ids)})
    return {
        "id": str(user.id),
        "full_name": full_name(user),
        "email": user.email,
        "university_id": user.university_id,
        "phone_last4": user.phone_last4,
        "must_change_password": user.must_change_password,
        "is_active": user.is_active,
        "archived_at": user.archived_at,
        "roles": roles,
    }
