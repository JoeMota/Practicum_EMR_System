from datetime import date

from app.models.clinical import (
    Appointment,
    ClinicalNote,
    Course,
    Patient,
    Referral,
)
from app.models.user import User
from app.services.access import full_name, memberships_for


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
        "instructor_ids": instructor_ids,
        "rubric_file_name": course.rubric_file_name,
    }


def patient_out(patient: Patient, *, owner_name: str | None) -> dict:
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
        "status": {
            "lifecycle": patient.lifecycle,
            "encounter": patient.encounter_status,
            "care_setting": patient.care_setting,
            "program": patient.program,
        },
        "allergies": [
            {"substance": a.substance, "reaction": a.reaction, "severity": a.severity} for a in patient.allergies
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
            }
            for m in patient.medications
        ],
        "problems": [{"code": p.code, "description": p.description, "since": p.since} for p in patient.problems],
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
        "vitals": [{"label": v.label, "value": v.value} for v in patient.vitals],
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
        },
        "emergency_contact": {
            "name": patient.emergency_contact_name,
            "phone": patient.emergency_contact_phone,
            "relationship": patient.emergency_contact_relationship,
        },
    }
    return payload


def note_out(note: ClinicalNote) -> dict:
    return {
        "id": str(note.id),
        "patient_id": str(note.patient_id),
        "encounter_id": str(note.encounter_id),
        "template_id": note.template_id,
        "author_id": str(note.author_id),
        "author_name": full_name(note.author),
        "author_discipline": note.discipline.code,
        "mode": note.mode,
        "status": note.status,
        "version": note.version,
        "content": note.content or {},
        "diagnoses": note.diagnoses or [],
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
                "body": item.body,
                "kind": item.kind,
                "created_at": item.created_at,
            }
            for item in sorted(note.feedback, key=lambda item: item.created_at)
        ],
        "addenda": [
            {
                "id": str(item.id),
                "author_name": full_name(item.author),
                "body": item.body,
                "created_at": item.created_at,
            }
            for item in sorted(note.addenda, key=lambda item: item.created_at)
        ],
    }


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
        "roles": roles,
    }
