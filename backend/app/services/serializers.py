"""Serialize ORM rows into the camelCase shapes the React app expects."""
from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import datetime
from typing import Any

from app.models.course import Course, Enrollment
from app.models.note import ClinicalNote
from app.models.patient import Patient
from app.models.scheduling import Appointment, Referral
from app.models.user import User
from app.schemas.clinical import (
    AppointmentOut,
    ClinicalNoteOut,
    CourseOut,
    PatientOut,
    ReferralOut,
    RoleAssignmentOut,
    SessionUserOut,
)


def _iso(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    return dt.isoformat()


def session_user_from(user: User, enrollments: list[Enrollment]) -> SessionUserOut:
    grouped: dict[tuple[str, str | None], list[str]] = defaultdict(list)
    for e in enrollments:
        key = (e.app_role, e.discipline_code)
        grouped[key].append(str(e.course_id))

    roles = [
        RoleAssignmentOut(role=role, discipline=disc, courseIds=sorted(set(ids)))
        for (role, disc), ids in grouped.items()
    ]
    # Users with global admin/instructor RBAC but no enrollments still need a role.
    if not roles:
        for r in user.roles:
            code = r.code
            if code in ("admin", "instructor", "front_desk", "patient"):
                roles.append(RoleAssignmentOut(role=code, courseIds=[]))
            elif code == "student" or code in (
                "physician", "nurse", "pharmacist", "physical_therapist",
                "occupational_therapist", "social_worker", "slp", "psychology",
            ):
                disc = user.discipline.code if user.discipline else None
                roles.append(RoleAssignmentOut(role="student", discipline=disc, courseIds=[]))

    return SessionUserOut(
        id=str(user.id),
        fullName=user.full_name,
        email=user.email,
        universityId=user.university_id,
        phoneLast4=user.phone_last4,
        roles=roles,
        mustChangePassword=user.must_change_password,
    )


def course_out(course: Course, instructor_ids: list[uuid.UUID]) -> CourseOut:
    return CourseOut(
        id=str(course.id),
        code=course.code,
        title=course.title,
        term=course.term,
        instructorIds=[str(i) for i in instructor_ids],
        rubricFileName=course.rubric_file_name,
    )


def patient_out(p: Patient, owner_name: str | None = None) -> PatientOut:
    return PatientOut(
        id=str(p.id),
        mrn=p.mrn,
        firstName=p.first_name,
        lastName=p.last_name,
        preferredName=p.preferred_name,
        dob=p.dob,
        ageYears=p.age_years,
        sexAtBirth=p.sex_at_birth,
        pronouns=p.pronouns,
        courseId=str(p.course_id),
        mode=p.mode,
        caseTemplateId=p.case_template_id,
        ownerId=str(p.owner_id) if p.owner_id else None,
        ownerName=owner_name,
        isTraining=p.is_training,
        practiceLabel=p.practice_label,
        chiefComplaint=p.chief_complaint,
        hpi=p.hpi,
        status=p.status or {},
        allergies=p.allergies or [],
        medications=p.medications or [],
        problems=p.problems or [],
        labs=p.labs or [],
        vitals=p.vitals or [],
        familyHistory=p.family_history or "",
        surgicalHistory=p.surgical_history or "",
        socialHistory=p.social_history or "",
        encounter=p.encounter or {},
    )


def note_out(n: ClinicalNote) -> ClinicalNoteOut:
    return ClinicalNoteOut(
        id=str(n.id),
        patientId=str(n.patient_id),
        encounterId=n.encounter_id,
        templateId=n.template_id,
        authorId=str(n.author_id),
        authorName=n.author_name,
        authorDiscipline=n.author_discipline,
        mode=n.mode,
        status=n.status,
        version=n.version,
        content=n.content or {},
        diagnoses=n.diagnoses or [],
        routedToId=str(n.routed_to_id) if n.routed_to_id else None,
        createdAt=_iso(n.created_at) or "",
        updatedAt=_iso(n.updated_at) or "",
        signedAt=_iso(n.signed_at),
        cosignedAt=_iso(n.cosigned_at),
        cosignedByName=n.cosigned_by_name,
        feedback=n.feedback or [],
        addenda=n.addenda or [],
    )


def appointment_out(a: Appointment) -> AppointmentOut:
    return AppointmentOut(
        id=str(a.id),
        patientId=str(a.patient_id),
        when=_iso(a.when) or "",
        kind=a.kind,
        withWhom=a.with_whom,
    )


def referral_out(r: Referral) -> ReferralOut:
    return ReferralOut(
        id=str(r.id),
        patientId=str(r.patient_id),
        toDiscipline=r.to_discipline,
        reason=r.reason,
        urgency=r.urgency,
        createdByName=r.created_by_name,
        createdAt=_iso(r.created_at) or "",
    )


def patient_snapshot_dict(p: Patient) -> dict[str, Any]:
    """Store enough to restore a practice patient on reset."""
    return {
        "mrn": p.mrn,
        "first_name": p.first_name,
        "last_name": p.last_name,
        "preferred_name": p.preferred_name,
        "dob": p.dob,
        "age_years": p.age_years,
        "sex_at_birth": p.sex_at_birth,
        "pronouns": p.pronouns,
        "chief_complaint": p.chief_complaint,
        "hpi": p.hpi,
        "family_history": p.family_history,
        "surgical_history": p.surgical_history,
        "social_history": p.social_history,
        "status": p.status,
        "allergies": p.allergies,
        "medications": p.medications,
        "problems": p.problems,
        "labs": p.labs,
        "vitals": p.vitals,
        "encounter": p.encounter,
        "practice_label": p.practice_label,
    }


def apply_patient_snapshot(p: Patient, snap: dict[str, Any]) -> None:
    for key, value in snap.items():
        setattr(p, key, value)
