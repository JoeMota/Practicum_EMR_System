"""Seed RBAC reference data + demo courses/users/patients for local development.

Run from backend/:
  python -m app.scripts.seed
  python -m app.scripts.seed --demo          # also load synthetic patients & demo logins
  python -m app.scripts.seed --admin-email admin@utep.edu

Demo password for all seeded accounts: practicum1
MFA code (dev): 123456
"""
from __future__ import annotations

import argparse
import asyncio
import getpass
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import selectinload

import app.models  # noqa: F401
from app.core.security import hash_password
from app.db.session import AsyncSessionLocal, engine
from app.models.course import Course, Enrollment
from app.models.note import ClinicalNote
from app.models.patient import Patient
from app.models.scheduling import Appointment
from app.models.user import Discipline, Permission, Role, User
from app.services.serializers import patient_snapshot_dict

PERMISSIONS = {
    "user:manage": "Create/edit accounts and assign roles",
    "audit:read": "Review the audit trail",
    "simulation:manage": "Create and reset simulated patients",
    "patient:read": "View patient charts",
    "patient:write": "Edit demographics, insurance, emergency contacts",
    "chart:write": "Edit history, allergies, problems, immunizations",
    "encounter:read": "View encounters",
    "encounter:write": "Create/close encounters",
    "note:write": "Write clinical notes",
    "note:cosign": "Co-sign student notes",
    "sensitive_note:read": "View psychology/psychiatry notes",
    "vitals:write": "Record vitals",
    "medication:read": "View medication list",
    "prescription:write": "Create simulated prescriptions",
    "scheduling:write": "Create/manage appointments",
}

DISCIPLINES = {
    "medicine": "Medicine",
    "nursing": "Nursing",
    "pharmacy": "Pharmacy",
    "physical_therapy": "Physical Therapy",
    "occupational_therapy": "Occupational Therapy",
    "social_work": "Social Work",
    "speech_language_pathology": "Speech-Language Pathology",
    "psychology": "Psychology / Psychiatry",
}

_THERAPY = ["patient:read", "encounter:read", "note:write", "medication:read"]
_STUDENT = [
    "patient:read", "encounter:read", "encounter:write", "note:write",
    "vitals:write", "medication:read", "prescription:write",
]

ROLES: dict[str, tuple[str, list[str]]] = {
    "admin": ("Administrator", list(PERMISSIONS)),
    "instructor": ("Instructor", [
        "user:manage", "audit:read", "simulation:manage", "patient:read",
        "encounter:read", "note:cosign", "medication:read", "sensitive_note:read",
    ]),
    "front_desk": ("Front Desk", ["patient:read", "patient:write", "scheduling:write"]),
    "student": ("Student", _STUDENT),
    "physician": ("Physician / Medical Provider", [
        "patient:read", "chart:write", "encounter:read", "encounter:write", "note:write",
        "vitals:write", "medication:read", "prescription:write",
    ]),
    "nurse": ("Nurse", [
        "patient:read", "chart:write", "encounter:read", "note:write", "vitals:write", "medication:read",
    ]),
    "pharmacist": ("Pharmacist / Pharmacy Student", _STUDENT),
    "physical_therapist": ("Physical Therapy", _THERAPY),
    "occupational_therapist": ("Occupational Therapy", _THERAPY),
    "social_worker": ("Social Work", _THERAPY),
    "slp": ("Speech-Language Pathology", _THERAPY),
    "psychology": ("Psychology / Psychiatry", _THERAPY + ["sensitive_note:read"]),
}

DEMO_PASSWORD = "practicum1"

# Stable UUIDs so re-seeds and docs stay consistent
UID = {
    "daniel": uuid.UUID("11111111-1111-1111-1111-111111111101"),
    "clarissa": uuid.UUID("11111111-1111-1111-1111-111111111102"),
    "gerardo": uuid.UUID("11111111-1111-1111-1111-111111111103"),
    "joe": uuid.UUID("11111111-1111-1111-1111-111111111104"),
    "sam": uuid.UUID("11111111-1111-1111-1111-111111111105"),
}
CID = {
    "phar": uuid.UUID("22222222-2222-2222-2222-222222222201"),
    "pt": uuid.UUID("22222222-2222-2222-2222-222222222202"),
}
PID = {
    "pa": uuid.UUID("33333333-3333-3333-3333-333333333301"),
    "pb": uuid.UUID("33333333-3333-3333-3333-333333333302"),
    "ae_daniel": uuid.UUID("33333333-3333-3333-3333-333333333303"),
    "ae_clarissa": uuid.UUID("33333333-3333-3333-3333-333333333304"),
    "ae_sam": uuid.UUID("33333333-3333-3333-3333-333333333305"),
}


async def seed_rbac(db, admin_email: str | None, admin_password: str | None) -> dict[str, Role]:
    existing = {p.code: p for p in (await db.scalars(select(Permission))).all()}
    for code, desc in PERMISSIONS.items():
        if code not in existing:
            existing[code] = Permission(code=code, description=desc)
            db.add(existing[code])

    have = {d.code: d for d in (await db.scalars(select(Discipline))).all()}
    for code, name in DISCIPLINES.items():
        if code not in have:
            d = Discipline(code=code, name=name)
            db.add(d)
            have[code] = d

    roles = {
        r.code: r
        for r in (await db.scalars(select(Role).options(selectinload(Role.permissions)))).all()
    }
    for code, (name, perm_codes) in ROLES.items():
        role = roles.get(code)
        if role is None:
            role = Role(code=code, name=name, permissions=[])
            db.add(role)
            roles[code] = role
        role.permissions = [existing[p] for p in perm_codes]

    if admin_email:
        email = admin_email.strip().lower()
        if await db.scalar(select(User).where(User.email == email)):
            print(f"Admin {email} already exists -- skipped.")
        else:
            db.add(User(
                email=email,
                first_name="Admin",
                last_name="User",
                hashed_password=hash_password(admin_password),
                must_change_password=False,
                roles=[roles["admin"]],
            ))
            print(f"Created admin {email}.")

    await db.flush()
    return roles


async def seed_demo(db, roles: dict[str, Role]) -> None:
    disciplines = {d.code: d for d in (await db.scalars(select(Discipline))).all()}
    pharmacy = disciplines["pharmacy"]
    hashed = hash_password(DEMO_PASSWORD)

    async def ensure_user(
        uid: uuid.UUID, email: str, first: str, last: str, *,
        uni: str | None, phone: str | None, role_codes: list[str], discipline_code: str | None,
    ) -> User:
        user = await db.get(User, uid)
        if user:
            return user
        user = User(
            id=uid,
            email=email,
            first_name=first,
            last_name=last,
            hashed_password=hashed,
            must_change_password=False,
            university_id=uni,
            phone_last4=phone,
            discipline_id=disciplines[discipline_code].id if discipline_code else None,
            roles=[roles[c] for c in role_codes],
        )
        db.add(user)
        await db.flush()
        return user

    daniel = await ensure_user(
        UID["daniel"], "daniel.reyes@miners.utep.edu", "Daniel", "Reyes",
        uni="800123456", phone="4412", role_codes=["student", "pharmacist"], discipline_code="pharmacy",
    )
    clarissa = await ensure_user(
        UID["clarissa"], "clarissa.dominguez@miners.utep.edu", "Clarissa", "Dominguez",
        uni="800654321", phone="9087", role_codes=["student", "pharmacist"], discipline_code="pharmacy",
    )
    gerardo = await ensure_user(
        UID["gerardo"], "gerardo.sillas@utep.edu", "Gerardo", "Sillas",
        uni=None, phone="2260", role_codes=["instructor", "admin"], discipline_code=None,
    )
    joe = await ensure_user(
        UID["joe"], "joe.mota@utep.edu", "Joe", "Mota",
        uni=None, phone="5521", role_codes=["instructor"], discipline_code=None,
    )
    sam = await ensure_user(
        UID["sam"], "sam.torres@miners.utep.edu", "Sam", "Torres",
        uni="800999001", phone="3344", role_codes=["student", "pharmacist"], discipline_code="pharmacy",
    )

    async def ensure_course(cid: uuid.UUID, code: str, title: str, term: str, rubric: str) -> Course:
        c = await db.get(Course, cid)
        if c:
            return c
        c = Course(id=cid, code=code, title=title, term=term, rubric_file_name=rubric)
        db.add(c)
        await db.flush()
        return c

    phar = await ensure_course(CID["phar"], "PHAR 5320", "Pharmacotherapy Skills Lab", "Fall 2026", "SOAP-note-rubric.pdf")
    pt = await ensure_course(CID["pt"], "PHYT 6310", "Clinical Practice I", "Fall 2026", "PT-daily-note-rubric.pdf")

    async def ensure_enrollment(user_id, course_id, app_role, discipline_code=None):
        q = select(Enrollment).where(
            Enrollment.user_id == user_id,
            Enrollment.course_id == course_id,
            Enrollment.app_role == app_role,
        )
        if discipline_code is None:
            q = q.where(Enrollment.discipline_code.is_(None))
        else:
            q = q.where(Enrollment.discipline_code == discipline_code)
        if (await db.execute(q)).scalar_one_or_none():
            return
        db.add(Enrollment(user_id=user_id, course_id=course_id, app_role=app_role, discipline_code=discipline_code))

    for u in (daniel, clarissa, sam):
        await ensure_enrollment(u.id, phar.id, "student", "pharmacy")
    await ensure_enrollment(gerardo.id, phar.id, "instructor")
    await ensure_enrollment(gerardo.id, phar.id, "admin")
    await ensure_enrollment(gerardo.id, pt.id, "instructor")
    await ensure_enrollment(gerardo.id, pt.id, "admin")
    await ensure_enrollment(joe.id, phar.id, "instructor")

    today = "2026-09-22"

    def t2dm(pid: uuid.UUID, owner: User, suffix: str) -> Patient:
        enc_id = f"enc_{pid}"
        return Patient(
            id=pid,
            mrn=f"TR-10057-{suffix}",
            first_name="Albert",
            last_name="Einstein",
            dob="1969-03-14",
            age_years=57,
            sex_at_birth="Male",
            pronouns="he/him",
            course_id=phar.id,
            mode="assessment",
            case_template_id="case_t2dm",
            owner_id=owner.id,
            is_training=True,
            chief_complaint='Diabetes follow-up. "My sugars have been running high."',
            hpi="57-year-old male with type 2 diabetes diagnosed 10 years ago, on metformin 500 mg daily. Reports home fasting readings of 180–230 mg/dL for the past 2 months. Occasionally misses the dose. Denies hypoglycemia. Reports increased thirst.",
            status={"lifecycle": "Active", "encounter": "Checked in", "careSetting": "Outpatient"},
            allergies=[{"substance": "Penicillin", "reaction": "Hives", "severity": "moderate"}],
            medications=[
                {"id": "m1", "name": "Metformin", "dose": "500 mg", "route": "PO", "frequency": "Once daily", "indication": "Type 2 diabetes", "adherence": "Misses ~2 doses/week"},
                {"id": "m2", "name": "Multivitamin", "dose": "1 tablet", "route": "PO", "frequency": "Once daily", "indication": "Supplement"},
            ],
            problems=[{"code": "E11.65", "description": "Type 2 diabetes mellitus with hyperglycemia", "since": "2016"}],
            labs=[
                {"id": "l1", "name": "Hemoglobin A1C", "value": "10.5", "unit": "%", "referenceRange": "4.0–5.6", "flag": "H", "collectedAt": "2026-09-15"},
                {"id": "l2", "name": "Fasting glucose", "value": "212", "unit": "mg/dL", "referenceRange": "70–99", "flag": "H", "collectedAt": "2026-09-15"},
            ],
            vitals=[
                {"label": "BP", "value": "138/86 mmHg"}, {"label": "Pulse", "value": "78 bpm"},
                {"label": "SpO₂", "value": "98%"}, {"label": "Weight", "value": "98 kg"},
            ],
            family_history="Mother: type 2 diabetes. Father: hypertension.",
            surgical_history="Appendectomy (1990).",
            social_history="Married. Never smoker. Alcohol 2 drinks/week. No drug use.",
            encounter={"id": enc_id, "type": "Office visit", "date": today},
        )

    async def ensure_patient(p: Patient) -> Patient:
        existing = await db.get(Patient, p.id)
        if existing:
            return existing
        if p.mode == "practice":
            await db.flush()
            p.practice_snapshot = patient_snapshot_dict(p)
        db.add(p)
        await db.flush()
        if p.mode == "practice" and not p.practice_snapshot:
            p.practice_snapshot = patient_snapshot_dict(p)
        return p

    pa = await ensure_patient(Patient(
        id=PID["pa"], mrn="TR-20001", first_name="Rosa", last_name="Villalobos", preferred_name="Rosie",
        dob="1958-07-02", age_years=68, sex_at_birth="Female", pronouns="she/her",
        course_id=phar.id, mode="practice", case_template_id="practice_a", is_training=True,
        practice_label="Test Patient A",
        chief_complaint="Blood pressure check and medication review.",
        hpi="68-year-old female with hypertension here for a 3-month follow-up. Reports occasional ankle swelling in the evenings.",
        status={"lifecycle": "Active", "encounter": "Checked in", "careSetting": "Outpatient"},
        allergies=[{"substance": "Sulfa drugs", "reaction": "Rash", "severity": "mild"}],
        medications=[
            {"id": "m1", "name": "Lisinopril", "dose": "10 mg", "route": "PO", "frequency": "Once daily", "indication": "Hypertension"},
            {"id": "m2", "name": "Amlodipine", "dose": "5 mg", "route": "PO", "frequency": "Once daily", "indication": "Hypertension"},
        ],
        problems=[{"code": "I10", "description": "Essential hypertension", "since": "2012"}],
        labs=[{"id": "l1", "name": "Potassium", "value": "4.6", "unit": "mmol/L", "referenceRange": "3.5–5.1", "collectedAt": "2026-09-10"}],
        vitals=[{"label": "BP", "value": "146/88 mmHg"}, {"label": "Pulse", "value": "72 bpm"}],
        family_history="Sister: stroke at 70.", surgical_history="Cholecystectomy (2004).",
        social_history="Widowed, lives alone. Former smoker, quit 2001.",
        encounter={"id": "enc_pa", "type": "Office visit", "date": today},
    ))
    # refresh snapshot after insert
    if not pa.practice_snapshot:
        pa.practice_snapshot = patient_snapshot_dict(pa)

    await ensure_patient(Patient(
        id=PID["pb"], mrn="TR-20002", first_name="Marcus", last_name="Hill",
        dob="1992-01-19", age_years=34, sex_at_birth="Male",
        course_id=pt.id, mode="practice", case_template_id="practice_b", is_training=True,
        practice_label="Test Patient B",
        chief_complaint="Right knee stiffness 6 weeks after ACL reconstruction.",
        hpi="34-year-old male, 6 weeks post right ACL reconstruction. Pain 3/10 with stairs.",
        status={"lifecycle": "Active", "encounter": "Scheduled", "careSetting": "Outpatient", "program": "Plan of care active"},
        allergies=[],
        medications=[{"id": "m1", "name": "Ibuprofen", "dose": "400 mg", "route": "PO", "frequency": "Every 8 hours as needed", "indication": "Knee pain"}],
        problems=[{"description": "Status post right ACL reconstruction", "since": "2026-08"}],
        labs=[],
        vitals=[{"label": "BP", "value": "122/78 mmHg"}, {"label": "Pulse", "value": "64 bpm"}],
        family_history="Noncontributory.", surgical_history="Right ACL reconstruction (Aug 2026).",
        social_history="Recreational soccer player. Office job.",
        encounter={"id": "enc_pb", "type": "PT visit #4", "date": today},
    ))

    await ensure_patient(t2dm(PID["ae_daniel"], daniel, "DR"))
    await ensure_patient(t2dm(PID["ae_clarissa"], clarissa, "CD"))
    ae_sam = await ensure_patient(t2dm(PID["ae_sam"], sam, "ST"))

    # Seed a pending-review note for Sam → Gerardo
    existing_note = (
        await db.execute(select(ClinicalNote).where(ClinicalNote.author_id == sam.id).limit(1))
    ).scalar_one_or_none()
    if not existing_note:
        db.add(ClinicalNote(
            patient_id=ae_sam.id,
            encounter_id=ae_sam.encounter["id"],
            template_id="pharmacy_mtm",
            author_id=sam.id,
            author_name=sam.full_name,
            author_discipline="pharmacy",
            mode="assessment",
            status="pending_review",
            version=4,
            content={
                "reason": "Diabetes follow-up, elevated home glucose.",
                "med_experience": "Takes metformin in the morning, forgets ~2x/week.",
                "objective": "A1C 10.5%, FBG 212. BP 138/86.",
                "dtp": "Needs additional therapy; adherence gaps.",
                "recommendations": "Titrate metformin; discuss second agent.",
            },
            diagnoses=[{"code": "E11.65", "label": "Type 2 diabetes mellitus with hyperglycemia"}],
            feedback=[],
            addenda=[],
            routed_to_id=gerardo.id,
            signed_at=datetime(2026, 9, 22, 15, 40, tzinfo=timezone.utc),
            archived=False,
        ))

    if not (await db.scalars(select(Appointment).where(Appointment.patient_id == ae_sam.id))).first():
        db.add(Appointment(
            patient_id=ae_sam.id,
            when=datetime(2026, 12, 15, 9, 30, tzinfo=timezone.utc),
            kind="Diabetes follow-up",
            with_whom="Pharmacy clinic",
        ))

    # Practice patient A should show scheduling content on the student demo path
    if not (await db.scalars(select(Appointment).where(Appointment.patient_id == pa.id))).first():
        db.add(Appointment(
            patient_id=pa.id,
            when=datetime(2026, 10, 6, 10, 0, tzinfo=timezone.utc),
            kind="BP follow-up / med review",
            with_whom="Pharmacy clinic",
        ))

    # Also seed a pending note routed to Joe so either instructor can demo review
    joe_note = (
        await db.execute(
            select(ClinicalNote).where(
                ClinicalNote.author_id == clarissa.id,
                ClinicalNote.routed_to_id == joe.id,
            ).limit(1)
        )
    ).scalar_one_or_none()
    if not joe_note:
        ae_clarissa = await db.get(Patient, PID["ae_clarissa"])
        if ae_clarissa:
            db.add(ClinicalNote(
                patient_id=ae_clarissa.id,
                encounter_id=ae_clarissa.encounter["id"],
                template_id="pharmacy_mtm",
                author_id=clarissa.id,
                author_name=clarissa.full_name,
                author_discipline="pharmacy",
                mode="assessment",
                status="pending_review",
                version=3,
                content={
                    "reason": "Diabetes follow-up.",
                    "objective": "A1C 10.5%, FBG 212.",
                    "recommendations": "Titrate metformin; adherence counseling.",
                },
                diagnoses=[{"code": "E11.65", "label": "Type 2 diabetes mellitus with hyperglycemia"}],
                feedback=[],
                addenda=[],
                routed_to_id=joe.id,
                signed_at=datetime(2026, 9, 22, 16, 10, tzinfo=timezone.utc),
                archived=False,
            ))

    print("Demo users (password: practicum1, MFA: 123456):")
    print("  Student:    daniel.reyes@miners.utep.edu  (write/sign notes)")
    print("  Student:    clarissa.dominguez@miners.utep.edu")
    print("  Student:    sam.torres@miners.utep.edu    (pre-submitted note)")
    print("  Instructor: gerardo.sillas@utep.edu       (review Sam's note; admin)")
    print("  Instructor: joe.mota@utep.edu             (review Clarissa's note)")


async def seed(admin_email: str | None, admin_password: str | None, demo: bool) -> None:
    async with AsyncSessionLocal() as db:
        roles = await seed_rbac(db, admin_email, admin_password)
        if demo:
            await seed_demo(db, roles)
        await db.commit()
    await engine.dispose()
    print(f"Seeded {len(PERMISSIONS)} permissions, {len(DISCIPLINES)} disciplines, {len(ROLES)} roles.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed EHR reference + demo data")
    parser.add_argument("--admin-email", help="Create an admin account with this email")
    parser.add_argument("--demo", action="store_true", help="Load synthetic courses, users, and patients")
    args = parser.parse_args()

    password = None
    if args.admin_email:
        password = getpass.getpass("Admin password (min 8 chars): ")
        if len(password) < 8:
            raise SystemExit("Password too short.")
        if password != getpass.getpass("Confirm password: "):
            raise SystemExit("Passwords don't match.")

    asyncio.run(seed(args.admin_email, password, args.demo))


if __name__ == "__main__":
    main()
