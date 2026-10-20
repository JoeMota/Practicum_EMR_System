"""Demo courses, users, and charts."""
import argparse
import asyncio
import getpass
import os
import uuid
from datetime import date, datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.orm import selectinload

import app.models  # noqa: F401
from app.core.config import settings
from app.core.security import hash_password
from app.db.session import AsyncSessionLocal, engine
from app.models.audit import AuditEvent
from app.models.clinical import (
    Allergy,
    Appointment,
    ClinicalNote,
    Course,
    NoteComment,
    CourseMembership,
    Encounter,
    LabResult,
    Medication,
    NoteAddendum,
    NoteComment,
    Patient,
    Problem,
    Referral,
    Vital,
)
from app.models.user import Discipline, Permission, Role, User
from app.services.access import ROLE_PERMISSIONS
from app.services.charts import chart_snapshot

NS = uuid.UUID("8f3c1a2e-6b4d-4e7a-9c11-2d5e6f708192")


def sid(key: str) -> uuid.UUID:
    return uuid.uuid5(NS, key)


DISCIPLINES = {
    "pharmacy": "Pharmacy",
    "physical_therapy": "Physical Therapy",
    "occupational_therapy": "Occupational Therapy",
    "speech_language_pathology": "Speech-Language Pathology",
    "nursing": "Nursing",
}

PERMISSIONS = {
    "patient:create": "Create a patient chart",
    "patient:update_status": "Change lifecycle, encounter, or care-setting status",
    "patient:reset_practice": "Restore a practice chart to its starting state",
    "encounter:advance": "Advance the encounter status during a visit",
    "note:author": "Write and sign a clinical note",
    "note:cosign": "Co-sign or return a student note",
    "referral:create": "Write a referral",
    "roster:import": "Import or remove students on a course roster",
    "instructor:remove": "Remove an instructor from a course",
    "course:create": "Create courses",
    "course:manage_status": "Start, end, or archive courses",
    "course:manage_access": "Manage course membership access",
    "user:manage_access": "Deactivate or reactivate user accounts",
    "report:run": "Run course reports",
    "audit:view": "Review the audit trail",
}


def _demo_password() -> str | None:
    if os.environ.get("SEED_DEMO_PASSWORD"):
        return os.environ["SEED_DEMO_PASSWORD"]
    if settings.ENVIRONMENT == "production":
        return None
    return "practicum-demo"


async def seed(admin_email: str | None, admin_password: str | None) -> None:
    async with AsyncSessionLocal() as db:
        permissions = await _upsert_permissions(db)
        disciplines = await _upsert_disciplines(db)
        roles = await _upsert_roles(db, permissions)
        await _drop_obsolete(db)
        await _seed_courses_and_people(db, roles, disciplines, _demo_password())
        if admin_email and admin_password:
            await _ensure_admin(db, roles["admin"], admin_email, admin_password)
        await db.commit()
    print(f"Seeded {len(PERMISSIONS)} permissions, {len(DISCIPLINES)} disciplines, {len(ROLE_PERMISSIONS)} roles.")


async def _upsert_permissions(db) -> dict[str, Permission]:
    existing = {row.code: row for row in (await db.scalars(select(Permission))).all()}
    for code, description in PERMISSIONS.items():
        if code not in existing:
            row = Permission(code=code, description=description)
            db.add(row)
            existing[code] = row
    await db.flush()
    return existing


async def _upsert_disciplines(db) -> dict[str, Discipline]:
    existing = {row.code: row for row in (await db.scalars(select(Discipline))).all()}
    for code, name in DISCIPLINES.items():
        if code not in existing:
            row = Discipline(code=code, name=name)
            db.add(row)
            existing[code] = row
    await db.flush()
    return existing


async def _upsert_roles(db, permissions: dict[str, Permission]) -> dict[str, Role]:
    existing = {
        row.code: row
        for row in (await db.scalars(select(Role).options(selectinload(Role.permissions)))).all()
    }
    names = {
        "student": "Student",
        "instructor": "Instructor",
        "admin": "Administrator",
        "front_desk": "Front Desk",
        "patient": "Patient",
    }
    for code, perm_codes in ROLE_PERMISSIONS.items():
        role = existing.get(code)
        if role is None:
            role = Role(code=code, name=names[code])
            db.add(role)
            existing[code] = role
            await db.flush()
        await db.refresh(role, attribute_names=["permissions"])
        role.permissions = [permissions[item] for item in perm_codes]
    await db.flush()
    return existing


async def _drop_obsolete(db) -> None:
    for role in (await db.scalars(select(Role))).all():
        if role.code not in ROLE_PERMISSIONS:
            await db.delete(role)
    for perm in (await db.scalars(select(Permission))).all():
        if perm.code not in PERMISSIONS:
            await db.delete(perm)
    all_disciplines = (await db.scalars(select(Discipline))).all()
    stale = [row.id for row in all_disciplines if row.code not in DISCIPLINES]
    if stale:
        await db.execute(update(User).where(User.discipline_id.in_(stale)).values(discipline_id=None))
        for row in all_disciplines:
            if row.code not in DISCIPLINES:
                await db.delete(row)
    await db.flush()


async def _seed_courses_and_people(db, roles, disciplines, password: str | None) -> None:
    if password is None:
        return
    phar = await _course(db, "PHAR 5320", "Pharmacotherapy Skills Lab", "Fall 2026", "SOAP-note-rubric.pdf")
    pt = await _course(db, "PHYT 6310", "Clinical Practice I", "Fall 2026", "PT-daily-note-rubric.pdf")
    hashed = hash_password(password)
    daniel = await _person(db, "daniel.reyes@miners.utep.edu", "Daniel", "Reyes", "800123456", "4412", hashed)
    clarissa = await _person(db, "clarissa.dominguez@miners.utep.edu", "Clarissa", "Dominguez", "800654321", "9087", hashed)
    gerardo = await _person(db, "gerardo.sillas@utep.edu", "Gerardo", "Sillas", None, "2260", hashed)
    joe = await _person(db, "joe.mota@utep.edu", "Joe", "Mota", None, "5521", hashed)
    ana = await _person(db, "ana.rios@miners.utep.edu", "Ana", "Rios", "800111111", None, hashed)
    sam = await _person(db, "sam.torres@miners.utep.edu", "Sam", "Torres", "800222222", None, hashed)
    luis = await _person(db, "luis.ortega@miners.utep.edu", "Luis", "Ortega", "800333333", None, hashed)
    if roles["admin"] not in gerardo.roles:
        gerardo.roles.append(roles["admin"])
    pharmacy = disciplines["pharmacy"]
    therapy = disciplines["physical_therapy"]
    await _member(db, daniel, phar, roles["student"], pharmacy)
    await _member(db, clarissa, phar, roles["student"], pharmacy)
    await _member(db, ana, phar, roles["student"], pharmacy)
    await _member(db, sam, phar, roles["student"], pharmacy)
    await _member(db, luis, pt, roles["student"], therapy)
    await _member(db, gerardo, phar, roles["instructor"], None)
    await _member(db, gerardo, pt, roles["instructor"], None)
    await _member(db, joe, phar, roles["instructor"], None)
    await _charts(db, phar, pt, ana, sam, luis, gerardo, daniel, clarissa)
    await _more_demo(db, phar, daniel, clarissa, ana, gerardo, pharmacy, therapy)
    await _mixed_names(db, phar, pt, daniel, luis, gerardo, joe, pharmacy, therapy, hashed)


async def _course(db, code: str, title: str, term: str, rubric: str) -> Course:
    course = await db.scalar(select(Course).where(Course.code == code, Course.term == term))
    if course is None:
        course = Course(code=code, title=title, term=term, rubric_file_name=rubric)
        db.add(course)
        await db.flush()
    return course


async def _person(db, email, first, last, university_id, phone, hashed) -> User:
    user = await db.scalar(select(User).options(selectinload(User.roles)).where(User.email == email))
    if user is None:
        user = User(
            email=email,
            first_name=first,
            last_name=last,
            university_id=university_id,
            phone_last4=phone,
            hashed_password=hashed,
            must_change_password=False,
            is_active=True,
        )
        db.add(user)
        await db.flush()
    await db.refresh(user, attribute_names=["roles"])
    return user


async def _member(db, user: User, course: Course, role: Role, discipline: Discipline | None) -> None:
    found = await db.scalar(
        select(CourseMembership).where(
            CourseMembership.user_id == user.id,
            CourseMembership.course_id == course.id,
            CourseMembership.role_id == role.id,
        )
    )
    if found is None:
        db.add(
            CourseMembership(
                user_id=user.id,
                course_id=course.id,
                role_id=role.id,
                discipline_id=discipline.id if discipline else None,
            )
        )


async def _ensure_admin(db, admin_role: Role, email: str, password: str) -> None:
    user = await db.scalar(select(User).options(selectinload(User.roles)).where(User.email == email.strip().lower()))
    if user:
        print(f"Admin {email} already exists -- skipped.")
        return
    db.add(
        User(
            email=email.strip().lower(),
            first_name="Admin",
            last_name="User",
            hashed_password=hash_password(password),
            must_change_password=False,
            roles=[admin_role],
        )
    )


async def _charts(
    db, phar: Course, pt: Course, ana: User, sam: User, luis: User, gerardo: User, daniel: User, clarissa: User,
) -> None:
    pharmacy = await db.scalar(select(Discipline).where(Discipline.code == "pharmacy"))
    therapy = await db.scalar(select(Discipline).where(Discipline.code == "physical_therapy"))
    nursing = await db.scalar(select(Discipline).where(Discipline.code == "nursing"))

    rosa = await _ensure_chart(db, "TR-20001", lambda: _rosa(phar))
    elena = await _ensure_chart(db, "TR-20003", lambda: _elena(phar))
    marcus = await _ensure_chart(db, "TR-20002", lambda: _marcus(pt))
    hector = await _ensure_chart(db, "TR-20004", lambda: _hector(phar))
    priya = await _ensure_chart(db, "TR-20005", lambda: _priya(phar))
    omar = await _ensure_chart(db, "TR-20006", lambda: _omar(phar))
    keisha = await _ensure_chart(db, "TR-20007", lambda: _keisha(phar))
    tomas = await _ensure_chart(db, "TR-20008", lambda: _tomas(phar))
    nadine = await _ensure_chart(db, "TR-20009", lambda: _nadine(phar))
    sofia = await _ensure_chart(db, "TR-20021", lambda: _sofia(pt))
    deshawn = await _ensure_chart(db, "TR-20022", lambda: _deshawn(pt))
    einstein_ana = await _ensure_chart(db, "TR-10057-AR", lambda: _t2dm(phar, ana, "TR-10057-AR"))
    einstein_sam = await _ensure_chart(db, "TR-10057-ST", lambda: _t2dm(phar, sam, "TR-10057-ST"))
    einstein_daniel = await _ensure_chart(db, "TR-10057-DR", lambda: _t2dm(phar, daniel, "TR-10057-DR"))
    einstein_clarissa = await _ensure_chart(db, "TR-10057-CD", lambda: _t2dm(phar, clarissa, "TR-10057-CD"))
    carmen = await _ensure_chart(db, "TR-10112-CD", lambda: _carmen(phar, clarissa))
    james = await _ensure_chart(db, "TR-10140-DR", lambda: _james(phar, daniel))
    linh = await _ensure_chart(db, "TR-10088-LO", lambda: _linh(pt, luis))

    _fill_rosa(rosa)
    _fill_elena(elena)
    _fill_marcus(marcus)
    _fill_hector(hector)
    _fill_priya(priya)
    _fill_omar(omar)
    _fill_keisha(keisha)
    _fill_tomas(tomas)
    _fill_nadine(nadine)
    _fill_sofia(sofia)
    _fill_deshawn(deshawn)
    for copy in (einstein_ana, einstein_sam, einstein_daniel, einstein_clarissa):
        _fill_t2dm(copy)
    _fill_carmen(carmen)
    _fill_james(james)
    _fill_linh(linh)
    await db.flush()

    for practice in (rosa, elena, marcus, hector, priya, omar, keisha, tomas, nadine, sofia, deshawn):
        await db.refresh(practice, attribute_names=["allergies", "medications", "problems", "labs", "vitals", "encounter"])
        if not practice.snapshot:
            practice.snapshot = chart_snapshot(practice)

    await _ensure_appointment(db, einstein_ana.id, datetime(2026, 12, 15, 9, 30, tzinfo=timezone.utc), "Diabetes follow-up", "Pharmacy clinic")
    await _ensure_appointment(db, einstein_daniel.id, datetime(2026, 10, 20, 14, 0, tzinfo=timezone.utc), "A1C recheck", "Pharmacy clinic")
    await _ensure_appointment(db, carmen.id, datetime(2026, 10, 8, 16, 0, tzinfo=timezone.utc), "INR follow-up", "Anticoagulation clinic")
    await _ensure_appointment(db, marcus.id, datetime(2026, 9, 29, 14, 0, tzinfo=timezone.utc), "PT visit #5", "Physical Therapy")
    await _ensure_appointment(db, linh.id, datetime(2026, 10, 2, 11, 0, tzinfo=timezone.utc), "PT visit #2", "Physical Therapy")
    await _ensure_appointment(db, hector.id, datetime(2026, 10, 9, 10, 0, tzinfo=timezone.utc), "COPD inhaler review", "Pharmacy clinic")
    await _ensure_appointment(db, priya.id, datetime(2026, 10, 14, 13, 30, tzinfo=timezone.utc), "Thyroid and lipids", "Pharmacy clinic")
    await _ensure_appointment(db, omar.id, datetime(2026, 10, 16, 9, 0, tzinfo=timezone.utc), "CKD / diabetes labs", "Pharmacy clinic")
    await _ensure_appointment(db, keisha.id, datetime(2026, 10, 7, 15, 0, tzinfo=timezone.utc), "Asthma follow-up", "Pharmacy clinic")
    await _ensure_appointment(db, sofia.id, datetime(2026, 10, 3, 8, 30, tzinfo=timezone.utc), "PT visit #6", "Physical Therapy")
    await _ensure_appointment(db, deshawn.id, datetime(2026, 10, 6, 11, 30, tzinfo=timezone.utc), "Gait training", "Physical Therapy")

    if nursing:
        await _ensure_referral(db, einstein_sam.id, nursing.id, gerardo.id, "Diabetes education and foot-care teaching.", "routine")
        await _ensure_referral(db, james.id, nursing.id, daniel.id, "Heart-failure daily-weight teaching.", "urgent")

    sam_note = await _ensure_note(
        db, einstein_sam, sam, pharmacy, gerardo,
        status="pending_review", template_id="pharmacy_mtm",
        content={
            "reason": "Diabetes follow-up, elevated home glucose.",
            "med_experience": "Takes metformin in the morning, forgets ~2x/week. No cost issues.",
            "objective": "A1C 10.5%, FBG 212, SCr 0.9, eGFR 92. BP 138/86.",
            "dtp": "Needs additional therapy: A1C far above goal on metformin monotherapy at low dose. Adherence: missed doses.",
            "rationale": "A1C >10% on low-dose metformin; renal function allows titration.",
            "recommendations": "1. Increase metformin to 1000 mg twice daily over 4 weeks.\n2. Discuss adding a second agent.",
            "followup": "Recheck A1C in 3 months.",
        },
        diagnoses=[{"code": "E11.65", "label": "Type 2 diabetes mellitus with hyperglycemia"}],
        created=datetime(2026, 9, 22, 15, 2, tzinfo=timezone.utc),
        signed=datetime(2026, 9, 22, 15, 40, tzinfo=timezone.utc),
    )
    await _ensure_audit(db, sam.id, "chart.view", "patient", einstein_sam.id, phar.id, datetime(2026, 9, 22, 15, 2, 11, tzinfo=timezone.utc))
    await _ensure_audit(db, sam.id, "note.sign_submit", "note", sam_note.id, phar.id, datetime(2026, 9, 22, 15, 40, 2, tzinfo=timezone.utc))

    ana_note = await _ensure_note(
        db, einstein_ana, ana, pharmacy, gerardo,
        status="cosigned", template_id="pharmacy_mtm",
        content={
            "reason": "Type 2 diabetes follow-up.",
            "med_experience": "Metformin 500 mg daily. Misses weekend doses when she works doubles.",
            "objective": "A1C 10.5%, FBG 212, eGFR 92, BP 138/86, BMI 30.9.",
            "dtp": "Indication: additional therapy needed. Adherence: weekend missed doses.",
            "rationale": "Far from goal on low-dose metformin; kidneys allow titration and a second agent.",
            "recommendations": "1. Titrate metformin to 1000 mg BID.\n2. Start empagliflozin 10 mg daily if coverage allows.",
            "monitoring": "BMP in 2 weeks, A1C in 3 months, counsel on genital hygiene.",
            "education": "Missed-dose plan and sick-day rules.",
            "followup": "Pharmacy clinic in 4 weeks.",
        },
        diagnoses=[{"code": "E11.65", "label": "Type 2 diabetes mellitus with hyperglycemia"}],
        created=datetime(2026, 9, 18, 13, 10, tzinfo=timezone.utc),
        signed=datetime(2026, 9, 18, 14, 5, tzinfo=timezone.utc),
        cosigned=datetime(2026, 9, 19, 9, 15, tzinfo=timezone.utc),
        cosigned_by=gerardo,
    )
    await _ensure_comment(db, ana_note, gerardo, "cosigned", "Clear assessment. Follow the empagliflozin coverage check before the next visit.")
    await _ensure_addendum(db, ana_note, ana, "Patient's insurance confirmed empagliflozin on formulary with a PA.")

    daniel_note = await _ensure_note(
        db, einstein_daniel, daniel, pharmacy, gerardo,
        status="returned", template_id="pharmacy_mtm",
        content={
            "reason": "High sugars.",
            "med_experience": "Takes metformin.",
            "objective": "A1C 10.5%.",
            "dtp": "Not at goal.",
            "rationale": "Needs a change.",
            "recommendations": "Increase metformin.",
            "followup": "Later.",
        },
        diagnoses=[{"code": "E11.65", "label": "Type 2 diabetes mellitus with hyperglycemia"}],
        created=datetime(2026, 9, 24, 16, 0, tzinfo=timezone.utc),
        signed=datetime(2026, 9, 24, 16, 20, tzinfo=timezone.utc),
        updated=datetime(2026, 9, 25, 10, 5, tzinfo=timezone.utc),
    )
    await _ensure_comment(
        db, daniel_note, gerardo, "returned",
        "Revise before resubmitting: (1) quantify missed doses and timing, (2) include SCr/eGFR before titrating metformin, (3) name a monitoring plan and a second-line option with rationale.",
    )
    await _ensure_audit(db, gerardo.id, "note.return", "note", daniel_note.id, phar.id, datetime(2026, 9, 25, 10, 5, tzinfo=timezone.utc))

    await _ensure_note(
        db, einstein_clarissa, clarissa, pharmacy, gerardo,
        status="draft", template_id="pharmacy_mtm",
        content={
            "reason": "Diabetes follow-up. Patient reports thirst and high home readings.",
            "med_experience": "Metformin 500 mg with breakfast. Skips it 1–2 mornings a week when rushing to class.",
        },
        diagnoses=[],
        created=datetime(2026, 9, 26, 11, 0, tzinfo=timezone.utc),
        updated=datetime(2026, 9, 26, 11, 45, tzinfo=timezone.utc),
    )

    carmen_note = await _ensure_note(
        db, carmen, clarissa, pharmacy, gerardo,
        status="returned", template_id="pharmacy_mtm",
        content={
            "reason": "Warfarin follow-up, INR high.",
            "med_experience": "Warfarin 5 mg daily. Occasional extra vitamin K foods. No missed doses this week.",
            "objective": "INR 4.8 (goal 2–3). No bleeding. BP 128/76.",
            "dtp": "Safety: supratherapeutic INR.",
            "rationale": "INR above goal; hold and restart lower.",
            "recommendations": "Hold warfarin today.",
            "followup": "Recheck INR.",
        },
        diagnoses=[{"code": "Z79.01", "label": "Long term (current) use of anticoagulants"}],
        created=datetime(2026, 9, 23, 9, 0, tzinfo=timezone.utc),
        signed=datetime(2026, 9, 23, 9, 40, tzinfo=timezone.utc),
        updated=datetime(2026, 9, 23, 15, 12, tzinfo=timezone.utc),
    )
    await _ensure_comment(
        db, carmen_note, gerardo, "returned",
        "Spell out hold vs dose reduction, when to restart, the exact next INR date, and bleeding precautions you gave the patient.",
    )

    await _ensure_note(
        db, james, daniel, pharmacy, gerardo,
        status="draft", template_id="pharmacy_mtm",
        content={
            "reason": "Heart failure med review after a weight gain of 4 lb.",
            "med_experience": "Furosemide 40 mg daily. Sometimes takes it later so he can leave the house.",
            "objective": "BP 110/68, pulse 88, K 3.3 (L), SCr 1.4.",
        },
        diagnoses=[{"code": "I50.22", "label": "Chronic systolic (congestive) heart failure"}],
        created=datetime(2026, 9, 27, 8, 30, tzinfo=timezone.utc),
    )

    await _ensure_note(
        db, rosa, daniel, pharmacy, None,
        status="signed", template_id="pharmacy_mtm",
        content={
            "reason": "BP follow-up.",
            "med_experience": "Lisinopril 10 mg and amlodipine 5 mg every morning. No missed doses. Ankle swelling in the evening.",
            "objective": "BP 146/88, pulse 72, K 4.6, SCr 1.1.",
            "dtp": "Effectiveness: BP above goal. Safety: amlodipine may be contributing to edema.",
            "rationale": "On two agents; edema suggests amlodipine. Kidney function supports current lisinopril.",
            "recommendations": "1. Keep lisinopril 10 mg daily.\n2. Discuss amlodipine vs. an ACE/ARB adjustment with the clinic.",
            "followup": "Recheck BP in 2 weeks at the skills lab.",
        },
        diagnoses=[{"code": "I10", "label": "Essential (primary) hypertension"}],
        created=datetime(2026, 9, 21, 10, 0, tzinfo=timezone.utc),
        signed=datetime(2026, 9, 21, 10, 25, tzinfo=timezone.utc),
        mode="practice",
    )

    if therapy:
        linh_note = await _ensure_note(
            db, linh, luis, therapy, gerardo,
            status="returned", template_id="pt_daily_soap",
            content={
                "visit_number": "1",
                "subjective": "Pain 6/10 in the right low back after lifting. Worse sitting.",
                "measures": "Lumbar flexion limited, SLR negative.",
                "interventions": "Education and gentle mobility.",
                "progress": "First visit.",
                "plan": "See twice a week.",
            },
            diagnoses=[{"code": "M54.50", "label": "Low back pain, unspecified"}],
            created=datetime(2026, 9, 22, 8, 0, tzinfo=timezone.utc),
            signed=datetime(2026, 9, 22, 8, 35, tzinfo=timezone.utc),
            updated=datetime(2026, 9, 22, 17, 0, tzinfo=timezone.utc),
        )
        await _ensure_comment(
            db, linh_note, gerardo, "returned",
            "Add measurable goals (ROM, pain, sitting tolerance), red-flag screen, and parameters for the HEP.",
        )


async def _ensure_chart(db, mrn: str, factory) -> Patient:
    found = await db.scalar(select(Patient).where(Patient.mrn == mrn))
    if found:
        return found
    chart = factory()
    db.add(chart)
    await db.flush()
    return chart


async def _ensure_appointment(db, patient_id, when, kind, with_whom) -> None:
    found = await db.scalar(
        select(Appointment.id).where(Appointment.patient_id == patient_id, Appointment.kind == kind)
    )
    if found is None:
        db.add(Appointment(patient_id=patient_id, when=when, kind=kind, with_whom=with_whom))


async def _ensure_referral(db, patient_id, discipline_id, created_by_id, reason, urgency) -> None:
    found = await db.scalar(
        select(Referral.id).where(Referral.patient_id == patient_id, Referral.reason == reason)
    )
    if found is None:
        db.add(Referral(
            patient_id=patient_id, to_discipline_id=discipline_id, reason=reason,
            urgency=urgency, created_by_id=created_by_id,
        ))


async def _ensure_note(
    db, patient: Patient, author: User, discipline, reviewer: User | None, *,
    status: str, template_id: str, content: dict, diagnoses: list, created: datetime,
    signed: datetime | None = None, updated: datetime | None = None,
    cosigned: datetime | None = None, cosigned_by: User | None = None, mode: str | None = None,
) -> ClinicalNote:
    found = await db.scalar(
        select(ClinicalNote).where(
            ClinicalNote.patient_id == patient.id,
            ClinicalNote.author_id == author.id,
            ClinicalNote.status == status,
        )
    )
    if found:
        return found
    note = ClinicalNote(
        patient_id=patient.id,
        encounter_id=patient.encounter.id,
        template_id=template_id,
        author_id=author.id,
        discipline_id=discipline.id,
        mode=mode or patient.mode,
        status=status,
        version=3 if status != "draft" else 1,
        content=content,
        diagnoses=diagnoses,
        routed_to_id=reviewer.id if reviewer else None,
        signed_at=signed,
        cosigned_at=cosigned,
        cosigned_by_id=cosigned_by.id if cosigned_by else None,
        created_at=created,
        updated_at=updated or signed or created,
    )
    db.add(note)
    await db.flush()
    return note


async def _ensure_comment(db, note: ClinicalNote, author: User, kind: str, body: str) -> None:
    found = await db.scalar(
        select(NoteComment.id).where(NoteComment.note_id == note.id, NoteComment.kind == kind, NoteComment.body == body)
    )
    if found is None:
        db.add(NoteComment(note_id=note.id, author_id=author.id, body=body, kind=kind, created_at=note.updated_at))


async def _ensure_addendum(db, note: ClinicalNote, author: User, body: str) -> None:
    found = await db.scalar(
        select(NoteAddendum.id).where(NoteAddendum.note_id == note.id, NoteAddendum.body == body)
    )
    if found is None:
        db.add(NoteAddendum(note_id=note.id, author_id=author.id, body=body, created_at=note.cosigned_at or note.updated_at))


async def _ensure_audit(db, actor_id, action, entity_type, entity_id, course_id, when) -> None:
    found = await db.scalar(
        select(AuditEvent.id).where(
            AuditEvent.actor_user_id == actor_id,
            AuditEvent.action == action,
            AuditEvent.entity_id == str(entity_id),
        )
    )
    if found is None:
        db.add(AuditEvent(
            occurred_at=when, actor_user_id=actor_id, action=action, entity_type=entity_type,
            entity_id=str(entity_id), result="ok", course_id=course_id,
        ))


def _maybe_allergy(chart: Patient, substance: str, reaction: str | None = None, severity: str | None = None) -> None:
    if not any(row.substance == substance for row in chart.allergies):
        chart.allergies.append(Allergy(substance=substance, reaction=reaction, severity=severity))


def _maybe_med(chart: Patient, name: str, **kwargs) -> None:
    if not any(row.name == name for row in chart.medications):
        chart.medications.append(Medication(name=name, **kwargs))


def _maybe_problem(chart: Patient, description: str, code: str | None = None, since: str | None = None) -> None:
    if not any(row.description == description for row in chart.problems):
        chart.problems.append(Problem(code=code, description=description, since=since))


def _maybe_lab(chart: Patient, name: str, collected_at: date, **kwargs) -> None:
    if not any(row.name == name and row.collected_at == collected_at for row in chart.labs):
        chart.labs.append(LabResult(name=name, collected_at=collected_at, **kwargs))


def _maybe_vital(chart: Patient, label: str, value: str) -> None:
    if not any(row.label == label for row in chart.vitals):
        chart.vitals.append(Vital(label=label, value=value))


def _contacts(chart: Patient, *, payer=None, member=None, group=None, em_name=None, em_phone=None, em_rel=None) -> None:
    if payer and not chart.insurance_payer:
        chart.insurance_payer = payer
    if member and not chart.insurance_member_id:
        chart.insurance_member_id = member
    if group and not chart.insurance_group_number:
        chart.insurance_group_number = group
    if em_name and not chart.emergency_contact_name:
        chart.emergency_contact_name = em_name
    if em_phone and not chart.emergency_contact_phone:
        chart.emergency_contact_phone = em_phone
    if em_rel and not chart.emergency_contact_relationship:
        chart.emergency_contact_relationship = em_rel


def _rosa(course: Course) -> Patient:
    chart = _patient(
        mrn="TR-20001", first="Rosa", last="Villalobos", preferred="Rosie", dob="1958-07-02", sex="Female",
        pronouns="she/her", course=course, mode="practice", case_key="practice_a", label="Test Patient A",
        cc="Blood pressure check and medication review.",
        hpi="68-year-old female with hypertension here for a 3-month follow-up. Reports occasional ankle swelling in the evenings. Home readings 140s/80s. Takes both BP pills with breakfast.",
        lifecycle="Active", encounter_status="Checked in", care="Outpatient",
        family="Sister: stroke at 70. Mother: hypertension.", surgical="Cholecystectomy (2004). Cataract OU (2019).",
        social="Widowed, lives alone. Former smoker, quit 2001 (30 pack-years). No alcohol. Walks the dog daily.",
        encounter_type="Office visit",
        payer="Medicare", member="1EG4-TE8-MK72", group="MED-A",
        em_name="Elena Villalobos", em_phone="915-555-0144", em_rel="Daughter",
    )
    _fill_rosa(chart)
    return chart


def _fill_rosa(chart: Patient) -> None:
    _contacts(chart, payer="Medicare", member="1EG4-TE8-MK72", group="MED-A",
              em_name="Elena Villalobos", em_phone="915-555-0144", em_rel="Daughter")
    _maybe_allergy(chart, "Sulfa drugs", "Rash", "mild")
    _maybe_allergy(chart, "Shellfish", "Hives", "moderate")
    _maybe_med(chart, "Lisinopril", dose="10 mg", route="PO", frequency="Once daily", indication="Hypertension", adherence="Takes every morning")
    _maybe_med(chart, "Amlodipine", dose="5 mg", route="PO", frequency="Once daily", indication="Hypertension", adherence="Takes every morning")
    _maybe_med(chart, "Hydrochlorothiazide", dose="12.5 mg", route="PO", frequency="Once daily", indication="Hypertension", adherence="Takes every morning")
    _maybe_med(chart, "Atorvastatin", dose="20 mg", route="PO", frequency="Once daily at bedtime", indication="Hyperlipidemia")
    _maybe_med(chart, "Aspirin", dose="81 mg", route="PO", frequency="Once daily", indication="Primary prevention")
    _maybe_problem(chart, "Essential hypertension", code="I10", since="2012")
    _maybe_problem(chart, "Hyperlipidemia", code="E78.5", since="2018")
    _maybe_problem(chart, "Lower extremity edema", code="R60.0")
    collected = date(2026, 9, 10)
    _maybe_lab(chart, "Potassium", collected, value="4.6", unit="mmol/L", reference_range="3.5–5.1")
    _maybe_lab(chart, "Serum creatinine", collected, value="1.1", unit="mg/dL", reference_range="0.6–1.1")
    _maybe_lab(chart, "eGFR", collected, value="52", unit="mL/min/1.73m²", reference_range=">60", flag="L")
    _maybe_lab(chart, "Sodium", collected, value="138", unit="mmol/L", reference_range="136–145")
    _maybe_lab(chart, "LDL cholesterol", collected, value="118", unit="mg/dL", reference_range="<100", flag="H")
    _maybe_vital(chart, "BP", "146/88 mmHg")
    _maybe_vital(chart, "Pulse", "72 bpm")
    _maybe_vital(chart, "Temp", "36.7 °C")
    _maybe_vital(chart, "SpO₂", "97%")
    _maybe_vital(chart, "Weight", "71 kg")
    _maybe_vital(chart, "Height", "160 cm")
    _maybe_vital(chart, "BMI", "27.7")


def _elena(course: Course) -> Patient:
    chart = _patient(
        mrn="TR-20003", first="Elena", last="Salazar", preferred=None, dob="1949-11-08", sex="Female",
        pronouns="she/her", course=course, mode="practice", case_key="practice_c", label="Test Patient C",
        cc="Warfarin teaching after a new DVT.",
        hpi="76-year-old female started on warfarin 5 days ago for a right-leg DVT. First clinic INR today. Using a pillbox. Diet includes spinach 3–4 nights a week.",
        lifecycle="Active", encounter_status="In progress", care="Outpatient",
        family="Brother: VTE at 62.", surgical="Right hip replacement (2021).",
        social="Lives with daughter. Rare alcohol. Never smoker.",
        encounter_type="Anticoagulation visit",
        payer="Medicare Advantage", member="MA-88421", group="UHC-ELP",
        em_name="Sofia Salazar", em_phone="915-555-0190", em_rel="Daughter",
    )
    _fill_elena(chart)
    return chart


def _fill_elena(chart: Patient) -> None:
    _contacts(chart, payer="Medicare Advantage", member="MA-88421", group="UHC-ELP",
              em_name="Sofia Salazar", em_phone="915-555-0190", em_rel="Daughter")
    _maybe_allergy(chart, "NSAIDs", "GI bleed", "severe")
    _maybe_med(chart, "Warfarin", dose="5 mg", route="PO", frequency="Once daily in the evening", indication="DVT", adherence="No missed doses")
    _maybe_med(chart, "Acetaminophen", dose="500 mg", route="PO", frequency="Every 8 hours as needed", indication="Hip pain")
    _maybe_med(chart, "Pantoprazole", dose="40 mg", route="PO", frequency="Once daily", indication="GI protection")
    _maybe_med(chart, "Calcium + vitamin D", dose="600 mg/400 IU", route="PO", frequency="Twice daily", indication="Bone health")
    _maybe_problem(chart, "Acute embolism and thrombosis of unspecified deep veins of right lower extremity", code="I82.401", since="2026-09")
    _maybe_problem(chart, "Long term (current) use of anticoagulants", code="Z79.01")
    _maybe_problem(chart, "Presence of right artificial hip joint", code="Z96.641", since="2021")
    _maybe_lab(chart, "INR", date(2026, 9, 26), value="1.4", unit="", reference_range="2.0–3.0", flag="L")
    _maybe_lab(chart, "Hemoglobin", date(2026, 9, 26), value="12.1", unit="g/dL", reference_range="12.0–16.0")
    _maybe_lab(chart, "Platelets", date(2026, 9, 26), value="248", unit="K/µL", reference_range="150–400")
    _maybe_vital(chart, "BP", "132/78 mmHg")
    _maybe_vital(chart, "Pulse", "76 bpm")
    _maybe_vital(chart, "Weight", "64 kg")
    _maybe_vital(chart, "SpO₂", "96%")


def _marcus(course: Course) -> Patient:
    chart = _patient(
        mrn="TR-20002", first="Marcus", last="Hill", preferred=None, dob="1992-01-19", sex="Male", pronouns="he/him",
        course=course, mode="practice", case_key="practice_b", label="Test Patient B",
        cc="Right knee stiffness 6 weeks after ACL reconstruction.",
        hpi="34-year-old male, 6 weeks post right ACL reconstruction. Pain 3/10 with stairs. Walking without crutches. Quad lag on straight-leg raise.",
        lifecycle="Active", encounter_status="Scheduled", care="Outpatient", program="Plan of care active",
        family="Father: OA of the knee.", surgical="Right ACL reconstruction (Aug 2026).",
        social="Recreational soccer player. Office job. Never smoker.",
        encounter_type="PT visit #4",
        payer="Blue Cross Community", member="BC-44019", group="UTEP-STAFF",
        em_name="Maya Hill", em_phone="915-555-0112", em_rel="Spouse",
    )
    _fill_marcus(chart)
    return chart


def _fill_marcus(chart: Patient) -> None:
    _contacts(chart, payer="Blue Cross Community", member="BC-44019", group="UTEP-STAFF",
              em_name="Maya Hill", em_phone="915-555-0112", em_rel="Spouse")
    _maybe_allergy(chart, "Latex", "Contact rash", "mild")
    _maybe_med(chart, "Ibuprofen", dose="400 mg", route="PO", frequency="Every 8 hours as needed", indication="Knee pain")
    _maybe_med(chart, "Acetaminophen", dose="500 mg", route="PO", frequency="Every 6 hours as needed", indication="Pain")
    _maybe_problem(chart, "Status post right ACL reconstruction", since="2026-08")
    _maybe_problem(chart, "Muscle weakness of right lower limb", code="M62.81")
    _maybe_vital(chart, "BP", "122/78 mmHg")
    _maybe_vital(chart, "Pulse", "64 bpm")
    _maybe_vital(chart, "Weight", "82 kg")
    _maybe_vital(chart, "Height", "183 cm")
    _maybe_vital(chart, "Pain", "3/10")


def _hector(course: Course) -> Patient:
    chart = _patient(
        mrn="TR-20004", first="Hector", last="Morales", preferred=None, dob="1955-03-22", sex="Male",
        pronouns="he/him", course=course, mode="practice", case_key="practice_copd", label="Test Patient D",
        cc="Short of breath and inhaler technique check.",
        hpi="71-year-old male with COPD. Using albuterol 4–5 times most days. Woke twice last week coughing. Continues to smoke ½ pack/day. No fever.",
        lifecycle="Active", encounter_status="Checked in", care="Outpatient",
        family="Father: lung cancer.", surgical="None.",
        social="Lives with wife. Current smoker 40 pack-years. Rare alcohol.",
        encounter_type="COPD clinic",
        payer="Medicare", member="1EG4-HM9-KX11", group="MED-B",
        em_name="Rosa Morales", em_phone="915-555-0177", em_rel="Spouse",
    )
    _fill_hector(chart)
    return chart


def _fill_hector(chart: Patient) -> None:
    _contacts(chart, payer="Medicare", member="1EG4-HM9-KX11", group="MED-B",
              em_name="Rosa Morales", em_phone="915-555-0177", em_rel="Spouse")
    _maybe_allergy(chart, "Penicillin", "Anaphylaxis", "severe")
    _maybe_med(chart, "Albuterol HFA", dose="90 mcg", route="Inh", frequency="2 puffs every 4–6 hours as needed", indication="Dyspnea", adherence="Uses 4–5 times/day")
    _maybe_med(chart, "Tiotropium", dose="18 mcg", route="Inh", frequency="Once daily", indication="COPD", adherence="Misses weekend doses")
    _maybe_med(chart, "Budesonide/formoterol", dose="160/4.5 mcg", route="Inh", frequency="2 puffs twice daily", indication="COPD")
    _maybe_med(chart, "Prednisone", dose="5 mg", route="PO", frequency="Once daily", indication="Recent exacerbation")
    _maybe_problem(chart, "COPD with (acute) exacerbation", code="J44.1", since="2014")
    _maybe_problem(chart, "Nicotine dependence, cigarettes", code="F17.210")
    _maybe_lab(chart, "Eosinophils", date(2026, 9, 12), value="180", unit="cells/µL", reference_range="<500")
    _maybe_vital(chart, "BP", "136/84 mmHg")
    _maybe_vital(chart, "Pulse", "92 bpm")
    _maybe_vital(chart, "RR", "22 /min")
    _maybe_vital(chart, "SpO₂", "91%")
    _maybe_vital(chart, "Weight", "68 kg")


def _priya(course: Course) -> Patient:
    chart = _patient(
        mrn="TR-20005", first="Priya", last="Nair", preferred=None, dob="1978-06-14", sex="Female",
        pronouns="she/her", course=course, mode="practice", case_key="practice_thyroid", label="Test Patient E",
        cc="Fatigue, weight gain, and lipid results.",
        hpi="48-year-old female with hypothyroidism on levothyroxine 75 mcg. Tired, cold, and up 6 lb since June. Last TSH was high. Also here for a statin start discussion.",
        lifecycle="Active", encounter_status="Waiting", care="Outpatient",
        family="Mother: hypothyroidism. Father: MI at 58.", surgical="C-section (2012).",
        social="Works nights in a call center. Vegetarian. No tobacco. Wine on weekends.",
        encounter_type="Office visit",
        payer="El Paso Health", member="EPH-22910", group="HOSP-RN",
        em_name="Arjun Nair", em_phone="915-555-0166", em_rel="Spouse",
    )
    _fill_priya(chart)
    return chart


def _fill_priya(chart: Patient) -> None:
    _contacts(chart, payer="El Paso Health", member="EPH-22910", group="HOSP-RN",
              em_name="Arjun Nair", em_phone="915-555-0166", em_rel="Spouse")
    _maybe_allergy(chart, "Iodine contrast", "Itching", "mild")
    _maybe_med(chart, "Levothyroxine", dose="75 mcg", route="PO", frequency="Once daily on empty stomach", indication="Hypothyroidism", adherence="Takes most mornings")
    _maybe_med(chart, "Omeprazole", dose="20 mg", route="PO", frequency="Once daily", indication="GERD")
    _maybe_med(chart, "Ethinyl estradiol/norgestimate", dose="35 mcg/0.25 mg", route="PO", frequency="Once daily", indication="Contraception")
    _maybe_problem(chart, "Hypothyroidism", code="E03.9", since="2019")
    _maybe_problem(chart, "Pure hypercholesterolemia", code="E78.00")
    _maybe_problem(chart, "GERD", code="K21.9")
    collected = date(2026, 9, 18)
    _maybe_lab(chart, "TSH", collected, value="8.4", unit="mIU/L", reference_range="0.4–4.0", flag="H")
    _maybe_lab(chart, "Free T4", collected, value="0.7", unit="ng/dL", reference_range="0.8–1.8", flag="L")
    _maybe_lab(chart, "LDL cholesterol", collected, value="162", unit="mg/dL", reference_range="<100", flag="H")
    _maybe_lab(chart, "HDL cholesterol", collected, value="48", unit="mg/dL", reference_range=">50", flag="L")
    _maybe_lab(chart, "Triglycerides", collected, value="178", unit="mg/dL", reference_range="<150", flag="H")
    _maybe_vital(chart, "BP", "128/82 mmHg")
    _maybe_vital(chart, "Pulse", "58 bpm")
    _maybe_vital(chart, "Weight", "79 kg")
    _maybe_vital(chart, "Height", "163 cm")
    _maybe_vital(chart, "BMI", "29.7")


def _omar(course: Course) -> Patient:
    chart = _patient(
        mrn="TR-20006", first="Omar", last="Haddad", preferred=None, dob="1964-11-02", sex="Male",
        pronouns="he/him", course=course, mode="practice", case_key="practice_ckd", label="Test Patient F",
        cc="Diabetes and kidney-function follow-up.",
        hpi="61-year-old male with type 2 diabetes and CKD. Metformin 1000 mg BID. Occasional foamy urine. Home fasting glucose 140–180. No chest pain.",
        lifecycle="Active", encounter_status="In progress", care="Outpatient",
        family="Brother: ESRD. Mother: type 2 diabetes.", surgical="Left eye cataract (2024).",
        social="Owns a small market. Former smoker, quit 2018. No alcohol.",
        encounter_type="CKD / diabetes visit",
        payer="Medicaid", member="TXM-77120", group="STAR",
        em_name="Layla Haddad", em_phone="915-555-0133", em_rel="Spouse",
    )
    _fill_omar(chart)
    return chart


def _fill_omar(chart: Patient) -> None:
    _contacts(chart, payer="Medicaid", member="TXM-77120", group="STAR",
              em_name="Layla Haddad", em_phone="915-555-0133", em_rel="Spouse")
    _maybe_allergy(chart, "ACE inhibitors", "Angioedema", "severe")
    _maybe_med(chart, "Metformin", dose="1000 mg", route="PO", frequency="Twice daily", indication="Type 2 diabetes", adherence="Rare missed lunch dose")
    _maybe_med(chart, "Losartan", dose="50 mg", route="PO", frequency="Once daily", indication="Hypertension / CKD")
    _maybe_med(chart, "Empagliflozin", dose="10 mg", route="PO", frequency="Once daily", indication="CKD / diabetes")
    _maybe_med(chart, "Atorvastatin", dose="40 mg", route="PO", frequency="Once daily at bedtime", indication="ASCVD prevention")
    _maybe_med(chart, "Insulin glargine", dose="18 units", route="SQ", frequency="Once daily at bedtime", indication="Type 2 diabetes")
    _maybe_problem(chart, "Type 2 diabetes mellitus with chronic kidney disease", code="E11.22", since="2012")
    _maybe_problem(chart, "CKD stage 3", code="N18.30", since="2022")
    _maybe_problem(chart, "Essential hypertension", code="I10")
    collected = date(2026, 9, 20)
    _maybe_lab(chart, "Hemoglobin A1C", collected, value="8.7", unit="%", reference_range="4.0–5.6", flag="H")
    _maybe_lab(chart, "Serum creatinine", collected, value="1.8", unit="mg/dL", reference_range="0.7–1.3", flag="H")
    _maybe_lab(chart, "eGFR", collected, value="41", unit="mL/min/1.73m²", reference_range=">60", flag="L")
    _maybe_lab(chart, "Potassium", collected, value="5.2", unit="mmol/L", reference_range="3.5–5.1", flag="H")
    _maybe_lab(chart, "UACR", collected, value="180", unit="mg/g", reference_range="<30", flag="H")
    _maybe_vital(chart, "BP", "148/90 mmHg")
    _maybe_vital(chart, "Pulse", "80 bpm")
    _maybe_vital(chart, "Weight", "96 kg")
    _maybe_vital(chart, "BMI", "31.4")


def _keisha(course: Course) -> Patient:
    chart = _patient(
        mrn="TR-20007", first="Keisha", last="Brooks", preferred=None, dob="1995-08-09", sex="Female",
        pronouns="she/her", course=course, mode="practice", case_key="practice_asthma", label="Test Patient G",
        cc="Asthma flare after a dusty move, also wants to talk about anxiety meds.",
        hpi="31-year-old female with asthma. Rescue inhaler 3 nights this week. Peak flow down from personal best. Started sertraline 4 weeks ago, nausea the first week.",
        lifecycle="Active", encounter_status="Checked in", care="Outpatient",
        family="Mother: asthma. Sister: GAD.", surgical="None.",
        social="Graduate student. Never smoker. Occasional vape with friends. Cat at home.",
        encounter_type="Urgent follow-up",
        payer="Student Health Plan", member="SHP-31088", group="UTEP-STU",
        em_name="Denise Brooks", em_phone="915-555-0188", em_rel="Mother",
    )
    _fill_keisha(chart)
    return chart


def _fill_keisha(chart: Patient) -> None:
    _contacts(chart, payer="Student Health Plan", member="SHP-31088", group="UTEP-STU",
              em_name="Denise Brooks", em_phone="915-555-0188", em_rel="Mother")
    _maybe_allergy(chart, "Aspirin", "Wheeze", "moderate")
    _maybe_allergy(chart, "Cats", "Sneezing", "mild")
    _maybe_med(chart, "Albuterol HFA", dose="90 mcg", route="Inh", frequency="2 puffs every 4 hours as needed", indication="Asthma", adherence="Used 8 puffs yesterday")
    _maybe_med(chart, "Fluticasone", dose="110 mcg", route="Inh", frequency="2 puffs twice daily", indication="Asthma", adherence="Skips nights when she feels well")
    _maybe_med(chart, "Montelukast", dose="10 mg", route="PO", frequency="Once daily at bedtime", indication="Asthma")
    _maybe_med(chart, "Sertraline", dose="50 mg", route="PO", frequency="Once daily", indication="Generalized anxiety")
    _maybe_med(chart, "Ethinyl estradiol/norethindrone", dose="20 mcg/1 mg", route="PO", frequency="Once daily", indication="Contraception")
    _maybe_problem(chart, "Uncomplicated asthma", code="J45.909", since="childhood")
    _maybe_problem(chart, "Generalized anxiety disorder", code="F41.1", since="2024")
    _maybe_problem(chart, "Allergic rhinitis", code="J30.9")
    _maybe_vital(chart, "BP", "118/74 mmHg")
    _maybe_vital(chart, "Pulse", "96 bpm")
    _maybe_vital(chart, "RR", "20 /min")
    _maybe_vital(chart, "SpO₂", "96%")
    _maybe_vital(chart, "Peak flow", "280 L/min")


def _tomas(course: Course) -> Patient:
    chart = _patient(
        mrn="TR-20008", first="Tomas", last="Alvarez", preferred="Tommy", dob="1969-12-01", sex="Male",
        pronouns="he/him", course=course, mode="practice", case_key="practice_gout", label="Test Patient H",
        cc="Right great-toe pain overnight. Wants to know if he can take more ibuprofen.",
        hpi="56-year-old male with recurrent gout. Red, hot first MTP, can't put a shoe on. Beer at a wedding Saturday. On HCTZ for BP.",
        lifecycle="Active", encounter_status="Checked in", care="Outpatient",
        family="Father: gout.", surgical="None.",
        social="Construction supervisor. Drinks beer on weekends. Never smoker.",
        encounter_type="Acute visit",
        payer="Cigna", member="CG-90144", group="CON-TX",
        em_name="Maria Alvarez", em_phone="915-555-0129", em_rel="Spouse",
    )
    _fill_tomas(chart)
    return chart


def _fill_tomas(chart: Patient) -> None:
    _contacts(chart, payer="Cigna", member="CG-90144", group="CON-TX",
              em_name="Maria Alvarez", em_phone="915-555-0129", em_rel="Spouse")
    _maybe_allergy(chart, "Allopurinol", "Rash", "moderate")
    _maybe_med(chart, "Ibuprofen", dose="800 mg", route="PO", frequency="Three times daily", indication="Gout pain", adherence="Took 2 extra tablets last night")
    _maybe_med(chart, "Hydrochlorothiazide", dose="25 mg", route="PO", frequency="Once daily", indication="Hypertension")
    _maybe_med(chart, "Lisinopril", dose="20 mg", route="PO", frequency="Once daily", indication="Hypertension")
    _maybe_med(chart, "Colchicine", dose="0.6 mg", route="PO", frequency="As directed for flares", indication="Gout", adherence="Ran out 2 weeks ago")
    _maybe_problem(chart, "Gout, unspecified", code="M10.9", since="2017")
    _maybe_problem(chart, "Essential hypertension", code="I10")
    _maybe_problem(chart, "Obesity, class 1", code="E66.9")
    collected = date(2026, 9, 28)
    _maybe_lab(chart, "Uric acid", collected, value="9.1", unit="mg/dL", reference_range="3.5–7.2", flag="H")
    _maybe_lab(chart, "Serum creatinine", collected, value="1.2", unit="mg/dL", reference_range="0.7–1.3")
    _maybe_lab(chart, "eGFR", collected, value="72", unit="mL/min/1.73m²", reference_range=">60")
    _maybe_vital(chart, "BP", "152/94 mmHg")
    _maybe_vital(chart, "Pulse", "88 bpm")
    _maybe_vital(chart, "Temp", "37.4 °C")
    _maybe_vital(chart, "Weight", "104 kg")
    _maybe_vital(chart, "BMI", "33.8")


def _nadine(course: Course) -> Patient:
    chart = _patient(
        mrn="TR-20009", first="Nadine", last="Chen", preferred=None, dob="1941-01-17", sex="Female",
        pronouns="she/her", course=course, mode="practice", case_key="practice_geriatric", label="Test Patient I",
        cc="Confusion and burning with urination. Family brought a bag of bottles.",
        hpi="85-year-old female from assisted living with 2 days of dysuria and new confusion. Fall last month, no fracture. Daughter is unsure which pills she actually takes.",
        lifecycle="Active", encounter_status="Waiting", care="Outpatient",
        family="Daughter is historian. No known CAD.", surgical="TKA right (2016). Pacemaker (2020).",
        social="Assisted living. Widowed. No tobacco or alcohol.",
        encounter_type="Geriatric visit",
        payer="Medicare", member="1EG4-NC2-PQ55", group="MED-A",
        em_name="Grace Chen", em_phone="915-555-0104", em_rel="Daughter",
    )
    _fill_nadine(chart)
    return chart


def _fill_nadine(chart: Patient) -> None:
    _contacts(chart, payer="Medicare", member="1EG4-NC2-PQ55", group="MED-A",
              em_name="Grace Chen", em_phone="915-555-0104", em_rel="Daughter")
    _maybe_allergy(chart, "Codeine", "Confusion", "moderate")
    _maybe_med(chart, "Donepezil", dose="10 mg", route="PO", frequency="Once daily at bedtime", indication="Dementia")
    _maybe_med(chart, "Metoprolol succinate", dose="50 mg", route="PO", frequency="Once daily", indication="AF / rate control")
    _maybe_med(chart, "Apixaban", dose="2.5 mg", route="PO", frequency="Twice daily", indication="Atrial fibrillation")
    _maybe_med(chart, "Oxybutynin", dose="5 mg", route="PO", frequency="Twice daily", indication="Overactive bladder")
    _maybe_med(chart, "Diphenhydramine", dose="25 mg", route="PO", frequency="At bedtime as needed", indication="Sleep")
    _maybe_med(chart, "Omeprazole", dose="20 mg", route="PO", frequency="Once daily", indication="GERD")
    _maybe_med(chart, "Vitamin D3", dose="2000 IU", route="PO", frequency="Once daily", indication="Deficiency")
    _maybe_problem(chart, "Urinary tract infection, site not specified", code="N39.0")
    _maybe_problem(chart, "Unspecified dementia, unspecified severity, with behavioral disturbance", code="F03.918", since="2021")
    _maybe_problem(chart, "Unspecified atrial fibrillation", code="I48.91")
    _maybe_problem(chart, "History of falling", code="Z91.81")
    collected = date(2026, 9, 29)
    _maybe_lab(chart, "WBC", collected, value="13.2", unit="K/µL", reference_range="4.0–11.0", flag="H")
    _maybe_lab(chart, "Sodium", collected, value="132", unit="mmol/L", reference_range="136–145", flag="L")
    _maybe_lab(chart, "Serum creatinine", collected, value="1.3", unit="mg/dL", reference_range="0.6–1.1", flag="H")
    _maybe_lab(chart, "UA nitrite", collected, value="Positive", unit="", reference_range="Negative", flag="H")
    _maybe_vital(chart, "BP", "108/64 mmHg")
    _maybe_vital(chart, "Pulse", "96 bpm")
    _maybe_vital(chart, "Temp", "38.1 °C")
    _maybe_vital(chart, "SpO₂", "95%")
    _maybe_vital(chart, "Weight", "52 kg")


def _sofia(course: Course) -> Patient:
    chart = _patient(
        mrn="TR-20021", first="Sofia", last="Ramirez", preferred=None, dob="1988-04-04", sex="Female",
        pronouns="she/her", course=course, mode="practice", case_key="practice_shoulder", label="Test Patient J",
        cc="Right shoulder pain reaching overhead at work.",
        hpi="38-year-old female, 8 weeks of right lateral shoulder pain after stocking shelves. Pain 5/10, worse at night. Positive painful arc. No neck pain or numbness.",
        lifecycle="Active", encounter_status="Scheduled", care="Outpatient", program="Plan of care active",
        family="Noncontributory.", surgical="None.",
        social="Grocery stocker, right-hand dominant. Yoga 1x/week.",
        encounter_type="PT visit #3",
        payer="UnitedHealthcare", member="UHC-55801", group="RETAIL-W",
        em_name="Luis Ramirez", em_phone="915-555-0155", em_rel="Spouse",
    )
    _fill_sofia(chart)
    return chart


def _fill_sofia(chart: Patient) -> None:
    _contacts(chart, payer="UnitedHealthcare", member="UHC-55801", group="RETAIL-W",
              em_name="Luis Ramirez", em_phone="915-555-0155", em_rel="Spouse")
    _maybe_med(chart, "Naproxen", dose="500 mg", route="PO", frequency="Twice daily", indication="Shoulder pain")
    _maybe_med(chart, "Cyclobenzaprine", dose="5 mg", route="PO", frequency="At bedtime as needed", indication="Muscle spasm")
    _maybe_problem(chart, "Unspecified rotator cuff tear or rupture of right shoulder, not specified as traumatic", code="M75.101")
    _maybe_vital(chart, "BP", "120/76 mmHg")
    _maybe_vital(chart, "Pulse", "72 bpm")
    _maybe_vital(chart, "Pain", "5/10")


def _deshawn(course: Course) -> Patient:
    chart = _patient(
        mrn="TR-20022", first="DeShawn", last="Carter", preferred=None, dob="1959-09-30", sex="Male",
        pronouns="he/him", course=course, mode="practice", case_key="practice_cva", label="Test Patient K",
        cc="Gait and balance after left MCA stroke 10 weeks ago.",
        hpi="66-year-old male, 10 weeks post left MCA ischemic stroke. Uses a cane. Residual right hemiparesis. Goal is independent household ambulation. No new weakness.",
        lifecycle="Active", encounter_status="Checked in", care="Outpatient", program="Plan of care active",
        family="Brother: stroke at 70.", surgical="PEG removed (2026).",
        social="Retired bus driver. Lives with son. Former smoker.",
        encounter_type="Neuro PT visit #8",
        payer="Medicare", member="1EG4-DC8-WW02", group="MED-B",
        em_name="Andre Carter", em_phone="915-555-0199", em_rel="Son",
    )
    _fill_deshawn(chart)
    return chart


def _fill_deshawn(chart: Patient) -> None:
    _contacts(chart, payer="Medicare", member="1EG4-DC8-WW02", group="MED-B",
              em_name="Andre Carter", em_phone="915-555-0199", em_rel="Son")
    _maybe_allergy(chart, "NKDA")
    _maybe_med(chart, "Aspirin", dose="81 mg", route="PO", frequency="Once daily", indication="Stroke secondary prevention")
    _maybe_med(chart, "Clopidogrel", dose="75 mg", route="PO", frequency="Once daily", indication="Stroke secondary prevention")
    _maybe_med(chart, "Atorvastatin", dose="80 mg", route="PO", frequency="Once daily at bedtime", indication="ASCVD")
    _maybe_med(chart, "Lisinopril", dose="10 mg", route="PO", frequency="Once daily", indication="Hypertension")
    _maybe_med(chart, "Metformin", dose="500 mg", route="PO", frequency="Twice daily", indication="Type 2 diabetes")
    _maybe_problem(chart, "Hemiplegia and hemiparesis following cerebral infarction affecting right dominant side", code="I69.351", since="2026-07")
    _maybe_problem(chart, "Type 2 diabetes mellitus without complications", code="E11.9")
    _maybe_problem(chart, "Essential hypertension", code="I10")
    _maybe_vital(chart, "BP", "134/80 mmHg")
    _maybe_vital(chart, "Pulse", "76 bpm")
    _maybe_vital(chart, "SpO₂", "97%")
    _maybe_vital(chart, "Weight", "88 kg")


def _carmen(course: Course, owner: User) -> Patient:
    chart = _patient(
        mrn="TR-10112-CD", first="Carmen", last="Ortiz", preferred=None, dob="1944-04-12", sex="Female",
        pronouns="she/her", course=course, mode="assessment", case_key="case_inr", owner=owner,
        cc="Warfarin follow-up. Last INR was high.",
        hpi="81-year-old female on warfarin for atrial fibrillation. Recent extra leafy greens at a family dinner. No bleeding, bruising on the forearm.",
        lifecycle="Active", encounter_status="Checked in", care="Outpatient",
        family="Mother: AF.", surgical="Cataract surgery (2019).", social="Lives independently. Daughter fills the pillbox.",
        encounter_type="Anticoagulation visit",
        payer="Medicare", member="1EG4-CO1-AF81", group="MED-A",
        em_name="Isabel Ortiz", em_phone="915-555-0148", em_rel="Daughter",
    )
    _fill_carmen(chart)
    return chart


def _fill_carmen(chart: Patient) -> None:
    _contacts(chart, payer="Medicare", member="1EG4-CO1-AF81", group="MED-A",
              em_name="Isabel Ortiz", em_phone="915-555-0148", em_rel="Daughter")
    _maybe_allergy(chart, "Aspirin", "Stomach upset", "mild")
    _maybe_med(chart, "Warfarin", dose="5 mg", route="PO", frequency="Once daily", indication="Atrial fibrillation", adherence="No missed doses this week")
    _maybe_med(chart, "Metoprolol tartrate", dose="25 mg", route="PO", frequency="Twice daily", indication="Rate control")
    _maybe_med(chart, "Furosemide", dose="20 mg", route="PO", frequency="Once daily", indication="Edema")
    _maybe_med(chart, "Levothyroxine", dose="50 mcg", route="PO", frequency="Once daily", indication="Hypothyroidism")
    _maybe_problem(chart, "Unspecified atrial fibrillation", code="I48.91", since="2018")
    _maybe_problem(chart, "Long term (current) use of anticoagulants", code="Z79.01")
    _maybe_problem(chart, "Hypothyroidism", code="E03.9")
    _maybe_lab(chart, "INR", date(2026, 9, 23), value="4.8", unit="", reference_range="2.0–3.0", flag="H")
    _maybe_lab(chart, "Hemoglobin", date(2026, 9, 23), value="11.4", unit="g/dL", reference_range="12.0–16.0", flag="L")
    _maybe_vital(chart, "BP", "128/76 mmHg")
    _maybe_vital(chart, "Pulse", "82 bpm")
    _maybe_vital(chart, "Weight", "58 kg")


def _james(course: Course, owner: User) -> Patient:
    chart = _patient(
        mrn="TR-10140-DR", first="James", last="Whitaker", preferred="Jim", dob="1952-02-02", sex="Male",
        pronouns="he/him", course=course, mode="assessment", case_key="case_hf", owner=owner,
        cc="Heart-failure med review after a 4 lb weight gain.",
        hpi="74-year-old male with HFrEF. Gained 4 lb in 5 days. More orthopnea. Taking furosemide later in the day so he can run errands.",
        lifecycle="Active", encounter_status="In progress", care="Outpatient",
        family="Father: MI at 68.", surgical="CABG (2015).", social="Retired mechanic. Wife cooks low-salt meals most days.",
        encounter_type="Heart failure clinic",
        payer="Medicare", member="1EG4-JW3-HF74", group="MED-B",
        em_name="Helen Whitaker", em_phone="915-555-0121", em_rel="Spouse",
    )
    _fill_james(chart)
    return chart


def _fill_james(chart: Patient) -> None:
    _contacts(chart, payer="Medicare", member="1EG4-JW3-HF74", group="MED-B",
              em_name="Helen Whitaker", em_phone="915-555-0121", em_rel="Spouse")
    _maybe_allergy(chart, "Lisinopril", "Cough", "moderate")
    _maybe_med(chart, "Furosemide", dose="40 mg", route="PO", frequency="Once daily", indication="Volume overload", adherence="Takes late morning")
    _maybe_med(chart, "Carvedilol", dose="12.5 mg", route="PO", frequency="Twice daily", indication="HFrEF")
    _maybe_med(chart, "Spironolactone", dose="25 mg", route="PO", frequency="Once daily", indication="HFrEF")
    _maybe_med(chart, "Sacubitril/valsartan", dose="49/51 mg", route="PO", frequency="Twice daily", indication="HFrEF")
    _maybe_med(chart, "Dapagliflozin", dose="10 mg", route="PO", frequency="Once daily", indication="HFrEF")
    _maybe_med(chart, "Atorvastatin", dose="40 mg", route="PO", frequency="Once daily at bedtime", indication="ASCVD")
    _maybe_problem(chart, "Chronic systolic (congestive) heart failure", code="I50.22", since="2015")
    _maybe_problem(chart, "Hyperlipidemia", code="E78.5")
    collected = date(2026, 9, 27)
    _maybe_lab(chart, "Potassium", collected, value="3.3", unit="mmol/L", reference_range="3.5–5.1", flag="L")
    _maybe_lab(chart, "Serum creatinine", collected, value="1.4", unit="mg/dL", reference_range="0.7–1.3", flag="H")
    _maybe_lab(chart, "BNP", collected, value="840", unit="pg/mL", reference_range="<100", flag="H")
    _maybe_lab(chart, "Sodium", collected, value="133", unit="mmol/L", reference_range="136–145", flag="L")
    _maybe_vital(chart, "BP", "110/68 mmHg")
    _maybe_vital(chart, "Pulse", "88 bpm")
    _maybe_vital(chart, "Weight", "92 kg")
    _maybe_vital(chart, "SpO₂", "94%")


def _linh(course: Course, owner: User) -> Patient:
    chart = _patient(
        mrn="TR-10088-LO", first="Linh", last="Nguyen", preferred=None, dob="1981-05-30", sex="Female",
        pronouns="she/her", course=course, mode="assessment", case_key="case_lbp", owner=owner,
        cc="Low back pain for 3 weeks after lifting boxes.",
        hpi="45-year-old female with low back pain radiating to the right buttock, worse with sitting. No numbness or bowel/bladder changes.",
        lifecycle="Active", encounter_status="Checked in", care="Outpatient",
        family="Noncontributory.", surgical="None.", social="Warehouse supervisor. Walks 3x/week.",
        encounter_type="PT evaluation",
        payer="Aetna", member="AE-10088", group="WH-ELP",
        em_name="Minh Nguyen", em_phone="915-555-0171", em_rel="Spouse",
    )
    _fill_linh(chart)
    return chart


def _fill_linh(chart: Patient) -> None:
    _contacts(chart, payer="Aetna", member="AE-10088", group="WH-ELP",
              em_name="Minh Nguyen", em_phone="915-555-0171", em_rel="Spouse")
    _maybe_allergy(chart, "Codeine", "Nausea", "mild")
    _maybe_med(chart, "Naproxen", dose="220 mg", route="PO", frequency="Twice daily", indication="Back pain")
    _maybe_med(chart, "Methocarbamol", dose="500 mg", route="PO", frequency="Three times daily as needed", indication="Spasm")
    _maybe_problem(chart, "Low back pain, unspecified", code="M54.50")
    _maybe_vital(chart, "BP", "118/74 mmHg")
    _maybe_vital(chart, "Pulse", "70 bpm")
    _maybe_vital(chart, "Pain", "6/10")
    _maybe_vital(chart, "Weight", "61 kg")


async def _more_demo(db, phar, daniel, clarissa, ana, gerardo, pharmacy, therapy) -> None:
    rosa = await db.scalar(select(Patient).where(Patient.mrn == "TR-20001"))
    if rosa is not None and not await db.scalar(select(Appointment.id).where(Appointment.patient_id == rosa.id)):
        db.add(Appointment(
            patient_id=rosa.id,
            when=datetime(2026, 10, 20, 15, 0, tzinfo=timezone.utc),
            kind="Blood pressure follow-up",
            with_whom="Pharmacy clinic",
        ))
        db.add(Referral(
            patient_id=rosa.id,
            to_discipline_id=therapy.id,
            reason="Ankle swelling on amlodipine. Please evaluate gait and edema.",
            urgency="routine",
            created_by_id=daniel.id,
        ))

    if await db.scalar(select(Patient.id).where(Patient.mrn == "TR-20003")) is None:
        elena = _patient(
            mrn="TR-20003", first="Elena", last="Vasquez", preferred=None, dob="1976-11-02", sex="Female",
            pronouns="she/her", course=phar, mode="practice", case_key="practice_c", label="Test Patient C",
            cc="Asthma follow-up. Using her rescue inhaler most days.",
            hpi="49-year-old female with asthma since childhood. Albuterol several times a day for the past month. Wakes up short of breath twice a week. No fever.",
            lifecycle="Active", encounter_status="Scheduled", care="Outpatient",
            family="Brother: asthma.", surgical="None.", social="Teacher. No tobacco. Cat at home.",
            encounter_type="Office visit",
        )
        elena.allergies.append(Allergy(substance="Aspirin", reaction="Wheezing", severity="moderate"))
        elena.medications.extend([
            Medication(name="Albuterol", dose="2 puffs", route="Inhaled", frequency="Every 4 hours as needed", indication="Asthma"),
            Medication(name="Fluticasone", dose="110 mcg", route="Inhaled", frequency="Twice daily", indication="Asthma", adherence="Misses evening dose"),
        ])
        elena.problems.append(Problem(code="J45.30", description="Mild persistent asthma, uncomplicated", since="childhood"))
        elena.labs.append(LabResult(name="Peak flow", value="310", unit="L/min", reference_range="380–450", flag="L", collected_at=date(2026, 10, 1)))
        elena.vitals.extend([
            Vital(label="BP", value="128/76 mmHg"), Vital(label="Pulse", value="88 bpm"),
            Vital(label="SpO₂", value="96%"), Vital(label="Weight", value="64 kg"),
        ])
        db.add(elena)
        await db.flush()
        await db.refresh(elena, attribute_names=["allergies", "medications", "problems", "labs", "vitals", "encounter"])
        elena.snapshot = chart_snapshot(elena)
        db.add(Appointment(
            patient_id=elena.id,
            when=datetime(2026, 10, 28, 16, 30, tzinfo=timezone.utc),
            kind="Inhaler technique check",
            with_whom="Pharmacy clinic",
        ))

    if await db.scalar(select(Patient.id).where(Patient.mrn == "TR-10021-DR")) is None:
        helen = _patient(
            mrn="TR-10021-DR", first="Helen", last="Cho", preferred=None, dob="1954-04-18", sex="Female",
            pronouns="she/her", course=phar, mode="assessment", case_key="case_hf", owner=daniel,
            cc="More short of breath when walking to the mailbox.",
            hpi="72-year-old female with heart failure. Weight up 4 pounds in a week. Taking furosemide most mornings. Ankles swollen by evening. No chest pain.",
            lifecycle="Active", encounter_status="In progress", care="Outpatient",
            family="Father: heart failure.", surgical="Hysterectomy (2008).", social="Lives with her daughter. No tobacco.",
            encounter_type="Office visit",
        )
        helen.allergies.append(Allergy(substance="Lisinopril", reaction="Cough", severity="mild"))
        helen.medications.extend([
            Medication(name="Furosemide", dose="20 mg", route="PO", frequency="Once daily", indication="Heart failure", adherence="Skips the dose when she has plans"),
            Medication(name="Carvedilol", dose="6.25 mg", route="PO", frequency="Twice daily", indication="Heart failure"),
        ])
        helen.problems.append(Problem(code="I50.22", description="Chronic systolic heart failure", since="2019"))
        helen.labs.append(LabResult(name="BNP", value="840", unit="pg/mL", reference_range="<100", flag="H", collected_at=date(2026, 10, 2)))
        helen.vitals.extend([
            Vital(label="BP", value="108/64 mmHg"), Vital(label="Pulse", value="92 bpm"),
            Vital(label="SpO₂", value="94%"), Vital(label="Weight", value="81 kg"),
        ])
        db.add(helen)
        await db.flush()
        db.add(ClinicalNote(
            patient_id=helen.id,
            encounter_id=helen.encounter.id,
            template_id="pharmacy_mtm",
            author_id=daniel.id,
            discipline_id=pharmacy.id,
            mode="assessment",
            status="draft",
            version=2,
            content={
                "reason": "Short of breath and a 4-pound weight gain.",
                "med_experience": "Takes furosemide in the morning. Skips it when she will be out of the house.",
            },
            diagnoses=[],
        ))

    if await db.scalar(select(Patient.id).where(Patient.mrn == "TR-10030-CD")) is None:
        oscar = _patient(
            mrn="TR-10030-CD", first="Oscar", last="Nguyen", preferred=None, dob="1961-08-09", sex="Male",
            pronouns="he/him", course=phar, mode="assessment", case_key="case_statin", owner=clarissa,
            cc="Here to talk about his cholesterol medicine.",
            hpi="64-year-old male with type 2 diabetes and an LDL of 148. Not on a statin. Says a neighbor told him statins ruin your muscles. No muscle pain now.",
            lifecycle="Active", encounter_status="Checked out", care="Outpatient",
            family="Mother: stroke at 68.", surgical="None.", social="Retired bus driver. Former smoker, quit 2015.",
            encounter_type="Office visit",
        )
        oscar.medications.append(Medication(name="Metformin", dose="1000 mg", route="PO", frequency="Twice daily", indication="Type 2 diabetes"))
        oscar.problems.extend([
            Problem(code="E11.9", description="Type 2 diabetes mellitus without complications", since="2014"),
            Problem(code="E78.5", description="Hyperlipidemia, unspecified", since="2024"),
        ])
        oscar.labs.append(LabResult(name="LDL cholesterol", value="148", unit="mg/dL", reference_range="<100", flag="H", collected_at=date(2026, 9, 28)))
        oscar.vitals.extend([Vital(label="BP", value="136/82 mmHg"), Vital(label="Pulse", value="74 bpm")])
        db.add(oscar)
        await db.flush()
        returned = ClinicalNote(
            patient_id=oscar.id,
            encounter_id=oscar.encounter.id,
            template_id="pharmacy_mtm",
            author_id=clarissa.id,
            discipline_id=pharmacy.id,
            mode="assessment",
            status="returned",
            version=3,
            content={
                "reason": "Cholesterol follow-up.",
                "recommendations": "Start a statin.",
                "rationale": "LDL is high.",
            },
            diagnoses=[{"code": "E78.5", "label": "Hyperlipidemia, unspecified"}],
            routed_to_id=gerardo.id,
            signed_at=datetime(2026, 10, 3, 18, 10, tzinfo=timezone.utc),
        )
        db.add(returned)
        await db.flush()
        db.add(NoteComment(
            note_id=returned.id,
            author_id=gerardo.id,
            body="Name the statin and dose, and say why a moderate-intensity statin fits this patient.",
            kind="returned",
            created_at=datetime(2026, 10, 4, 15, 0, tzinfo=timezone.utc),
        ))

    ana_chart = await db.scalar(select(Patient).where(Patient.mrn == "TR-10057-AR"))
    if ana_chart is not None and not await db.scalar(select(ClinicalNote.id).where(ClinicalNote.patient_id == ana_chart.id, ClinicalNote.archived.is_(False))):
        done = datetime(2026, 9, 30, 17, 5, tzinfo=timezone.utc)
        db.add(ClinicalNote(
            patient_id=ana_chart.id,
            encounter_id=ana_chart.encounter.id,
            template_id="pharmacy_mtm",
            author_id=ana.id,
            discipline_id=pharmacy.id,
            mode="assessment",
            status="cosigned",
            version=5,
            content={
                "reason": "Diabetes follow-up, home glucose 180–230.",
                "recommendations": "Increase metformin to 1000 mg twice daily. Recheck A1C in 3 months.",
                "rationale": "A1C 10.5% on metformin 500 mg daily, with missed doses. Renal function is fine.",
            },
            diagnoses=[{"code": "E11.65", "label": "Type 2 diabetes mellitus with hyperglycemia"}],
            routed_to_id=gerardo.id,
            signed_at=datetime(2026, 9, 30, 16, 40, tzinfo=timezone.utc),
            cosigned_at=done,
            cosigned_by_id=gerardo.id,
            updated_at=done,
        ))


def _t2dm(course: Course, owner: User, mrn: str) -> Patient:
    chart = _patient(
        mrn=mrn, first="Albert", last="Einstein", preferred=None, dob="1969-03-14", sex="Male", pronouns="he/him",
        course=course, mode="assessment", case_key="case_t2dm", owner=owner,
        cc='Diabetes follow-up. "My sugars have been running high."',
        hpi="57-year-old male with type 2 diabetes diagnosed 10 years ago, on metformin 500 mg daily. Reports home fasting readings of 180–230 mg/dL for the past 2 months. Occasionally misses the dose. Denies hypoglycemia. Reports increased thirst.",
        lifecycle="Active", encounter_status="Checked in", care="Outpatient",
        family="Mother: type 2 diabetes. Father: hypertension.", surgical="Appendectomy (1990).",
        social="Married. Never smoker. Alcohol 2 drinks/week. No drug use. Takes a daily multivitamin.",
        encounter_type="Office visit",
        payer="Blue Cross", member="BC-10057", group="FAC-ELP",
        em_name="Elsa Einstein", em_phone="915-555-0100", em_rel="Spouse",
    )
    _fill_t2dm(chart)
    return chart


def _fill_t2dm(chart: Patient) -> None:
    _contacts(chart, payer="Blue Cross", member="BC-10057", group="FAC-ELP",
              em_name="Elsa Einstein", em_phone="915-555-0100", em_rel="Spouse")
    _maybe_allergy(chart, "Penicillin", "Hives", "moderate")
    _maybe_med(chart, "Metformin", dose="500 mg", route="PO", frequency="Once daily", indication="Type 2 diabetes", adherence="Misses ~2 doses/week")
    _maybe_med(chart, "Multivitamin", dose="1 tablet", route="PO", frequency="Once daily", indication="Supplement")
    for med in list(chart.medications):
        if med.name in {"Lisinopril", "Atorvastatin"}:
            chart.medications.remove(med)
    _maybe_problem(chart, "Type 2 diabetes mellitus with hyperglycemia", code="E11.65", since="2016")
    collected = date(2026, 9, 15)
    _maybe_lab(chart, "Hemoglobin A1C", collected, value="10.5", unit="%", reference_range="4.0–5.6", flag="H")
    _maybe_lab(chart, "Fasting glucose", collected, value="212", unit="mg/dL", reference_range="70–99", flag="H")
    _maybe_lab(chart, "Serum creatinine", collected, value="0.9", unit="mg/dL", reference_range="0.7–1.3")
    _maybe_lab(chart, "eGFR", collected, value="92", unit="mL/min/1.73m²", reference_range=">60")
    _maybe_lab(chart, "Potassium", collected, value="4.2", unit="mmol/L", reference_range="3.5–5.1")
    _maybe_lab(chart, "LDL cholesterol", collected, value="96", unit="mg/dL", reference_range="<100")
    _maybe_vital(chart, "BP", "138/86 mmHg")
    _maybe_vital(chart, "Pulse", "78 bpm")
    _maybe_vital(chart, "SpO₂", "98%")
    _maybe_vital(chart, "Weight", "98 kg")
    _maybe_vital(chart, "Height", "178 cm")
    _maybe_vital(chart, "BMI", "30.9")


def _patient(**kwargs) -> Patient:
    return Patient(
        mrn=kwargs["mrn"],
        first_name=kwargs["first"],
        last_name=kwargs["last"],
        preferred_name=kwargs.get("preferred"),
        dob=date.fromisoformat(kwargs["dob"]),
        sex_at_birth=kwargs["sex"],
        pronouns=kwargs.get("pronouns"),
        course_id=kwargs["course"].id,
        mode=kwargs["mode"],
        case_key=kwargs["case_key"],
        owner_id=kwargs["owner"].id if kwargs.get("owner") else None,
        practice_label=kwargs.get("label"),
        chief_complaint=kwargs["cc"],
        hpi=kwargs["hpi"],
        lifecycle=kwargs["lifecycle"],
        encounter_status=kwargs["encounter_status"],
        care_setting=kwargs["care"],
        program=kwargs.get("program"),
        family_history=kwargs["family"],
        surgical_history=kwargs["surgical"],
        social_history=kwargs["social"],
        insurance_payer=kwargs.get("payer"),
        insurance_member_id=kwargs.get("member"),
        insurance_group_number=kwargs.get("group"),
        emergency_contact_name=kwargs.get("em_name"),
        emergency_contact_phone=kwargs.get("em_phone"),
        emergency_contact_relationship=kwargs.get("em_rel"),
        is_training=True,
        encounter=Encounter(type=kwargs["encounter_type"], date=date(2026, 9, 22)),
    )


async def _mixed_names(db, phar, pt, daniel, luis, gerardo, joe, pharmacy, therapy, hashed) -> None:
    role = await db.scalar(select(Role).where(Role.code == "student"))
    roster = [
        ("peter.parker@miners.utep.edu", "Peter", "Parker", "800701001", "1001", phar, pharmacy),
        ("wanda.maximoff@miners.utep.edu", "Wanda", "Maximoff", "800701002", "1002", phar, pharmacy),
        ("stephen.strange@miners.utep.edu", "Stephen", "Strange", "800701003", "1003", phar, pharmacy),
        ("scott.lang@miners.utep.edu", "Scott", "Lang", "800701004", "1004", phar, pharmacy),
        ("maria.gonzalez@miners.utep.edu", "Maria", "Gonzalez", "800703001", "3301", phar, pharmacy),
        ("diego.ramirez@miners.utep.edu", "Diego", "Ramirez", "800703002", "3302", phar, pharmacy),
        ("bucky.barnes@miners.utep.edu", "Bucky", "Barnes", "800702001", "2001", pt, therapy),
        ("jessica.jones@miners.utep.edu", "Jessica", "Jones", "800702002", "2002", pt, therapy),
        ("matt.murdock@miners.utep.edu", "Matt", "Murdock", "800702003", "2003", pt, therapy),
        ("andres.morales@miners.utep.edu", "Andres", "Morales", "800704001", "4401", pt, therapy),
        ("valeria.castillo@miners.utep.edu", "Valeria", "Castillo", "800704002", "4402", pt, therapy),
    ]
    users = {}
    for email, first, last, uid, phone, course, disc in roster:
        user = await _person(db, email, first, last, uid, phone, hashed)
        await _member(db, user, course, role, disc)
        users[email] = user

    async def chart(mrn, first, last, dob, sex, course, mode, owner, visit, cc, med, dose, problem, code, lab=None):
        etype = "Office visit" if course is phar else "PT evaluation"
        row = await _ensure_chart(db, mrn, lambda: _patient(
            mrn=mrn, first=first, last=last, dob=dob, sex=sex,
            pronouns="she/her" if sex == "Female" else "he/him",
            course=course, mode=mode, case_key=mrn.lower(),
            label=f"Test Patient {last}" if mode == "practice" else None,
            owner=owner, cc=cc, hpi=cc,
            lifecycle="Active", encounter_status=visit, care="Outpatient",
            family="Noncontributory.", surgical="None.", social="Lives in El Paso. No current tobacco.",
            encounter_type=etype,
        ))
        await db.refresh(row, attribute_names=["allergies", "medications", "problems", "labs", "vitals", "encounter"])
        inhaled = med == "Albuterol"
        _maybe_med(
            row, med, dose=dose, route="Inhaled" if inhaled else "PO",
            frequency="Every 4 hours as needed" if inhaled else "Once daily", indication=problem,
        )
        _maybe_problem(row, problem, code=code, since="2024")
        _maybe_vital(row, "BP", "124/76 mmHg")
        _maybe_vital(row, "Pulse", "72 bpm")
        if lab:
            _maybe_lab(row, lab[0], date(2026, 10, 1), value=lab[1], unit=lab[2], reference_range=lab[3], flag=lab[4])
        if mode == "practice" and not row.snapshot:
            row.snapshot = chart_snapshot(row)
        return row

    charts = {
        "TR-M-STARK": await chart("TR-M-STARK", "Tony", "Stark", "1970-05-29", "Male", phar, "practice", None, "Checked in", "Chest tightness after he skips his evening water pill.", "Furosemide", "40 mg", "Chronic systolic heart failure", "I50.22", ("BNP", "910", "pg/mL", "<100", "H")),
        "TR-M-POTTS": await chart("TR-M-POTTS", "Pepper", "Potts", "1972-02-12", "Female", phar, "practice", None, "Scheduled", "Blood pressure still high on two medicines.", "Lisinopril", "20 mg", "Essential hypertension", "I10"),
        "TR-M-HOGAN": await chart("TR-M-HOGAN", "Happy", "Hogan", "1968-08-03", "Male", phar, "practice", None, "Checked out", "Morning sugars in the 160s.", "Metformin", "1000 mg", "Type 2 diabetes mellitus", "E11.9", ("Hemoglobin A1C", "7.4", "%", "4.0–5.6", "H")),
        "TR-X-MORALES": await chart("TR-X-MORALES", "Guadalupe", "Morales", "1956-12-12", "Female", phar, "practice", None, "Checked in", "Blood pressure still high. Takes her medicine with breakfast.", "Lisinopril", "20 mg", "Essential hypertension", "I10", ("Potassium", "5.4", "mmol/L", "3.5–5.1", "H")),
        "TR-X-HERNANDEZ": await chart("TR-X-HERNANDEZ", "Jose", "Hernandez", "1964-03-21", "Male", phar, "practice", None, "Scheduled", "Refill on metformin. Sugars better since he cut soda.", "Metformin", "1000 mg", "Type 2 diabetes mellitus", "E11.9"),
        "TR-M-DANVERS": await chart("TR-M-DANVERS", "Carol", "Danvers", "1985-04-24", "Female", pt, "practice", None, "Checked in", "Right shoulder pain after a fall last week.", "Ibuprofen", "400 mg", "Pain in right shoulder", "M25.511", ("CRP", "18", "mg/L", "<10", "H")),
        "TR-M-KHAN": await chart("TR-M-KHAN", "Kamala", "Khan", "2004-08-14", "Female", pt, "practice", None, "Scheduled", "Ankle sprain from basketball, two weeks ago.", "Ibuprofen", "400 mg", "Sprain of right ankle", "S93.401A"),
        "TR-X-AGUILAR": await chart("TR-X-AGUILAR", "Beatriz", "Aguilar", "1974-08-30", "Female", pt, "practice", None, "Checked in", "Right knee pain after a fall in the kitchen.", "Acetaminophen", "500 mg", "Pain in right knee", "M25.561"),
        "TR-M-FURY": await chart("TR-M-FURY", "Nick", "Fury", "1950-07-04", "Male", phar, "assessment", users["peter.parker@miners.utep.edu"], "In progress", "Home readings still in the 150s after a ministroke scare.", "Amlodipine", "5 mg", "Essential hypertension", "I10", ("LDL cholesterol", "128", "mg/dL", "<70", "H")),
        "TR-M-MAY": await chart("TR-M-MAY", "May", "Parker", "1948-05-08", "Female", phar, "assessment", users["peter.parker@miners.utep.edu"], "Checked out", "Lightheaded after her blood pressure medicine was raised.", "Lisinopril", "20 mg", "Essential hypertension", "I10"),
        "TR-M-PIETRO": await chart("TR-M-PIETRO", "Pietro", "Maximoff", "1988-02-10", "Male", phar, "assessment", users["wanda.maximoff@miners.utep.edu"], "Checked in", "Says his rescue inhaler makes his heart race.", "Albuterol", "2 puffs", "Mild intermittent asthma", "J45.20"),
        "TR-M-VISION": await chart("TR-M-VISION", "Vision", "Shade", "1985-05-02", "Male", phar, "assessment", users["wanda.maximoff@miners.utep.edu"], "Checked in", "Ankle swelling on his calcium channel blocker.", "Amlodipine", "10 mg", "Essential hypertension", "I10"),
        "TR-M-WONG": await chart("TR-M-WONG", "Wong", "Kamar-Taj", "1966-01-09", "Male", phar, "assessment", users["stephen.strange@miners.utep.edu"], "Scheduled", "Heartburn most nights. Takes calcium at bedtime.", "Omeprazole", "20 mg", "Gastro-esophageal reflux disease", "K21.9"),
        "TR-M-PALMER": await chart("TR-M-PALMER", "Christine", "Palmer", "1979-07-19", "Female", phar, "assessment", users["stephen.strange@miners.utep.edu"], "Checked out", "Bruising on warfarin. Missed two doses last week.", "Warfarin", "5 mg", "Atrial fibrillation", "I48.91"),
        "TR-M-LEWIS": await chart("TR-M-LEWIS", "Darcy", "Lewis", "1990-03-12", "Female", phar, "assessment", users["scott.lang@miners.utep.edu"], "In progress", "Morning sugars in the 180s on metformin alone.", "Metformin", "500 mg", "Type 2 diabetes mellitus", "E11.9"),
        "TR-M-SELVIG": await chart("TR-M-SELVIG", "Erik", "Selvig", "1955-11-02", "Male", phar, "assessment", users["scott.lang@miners.utep.edu"], "Checked out", "Calf cramps on his water pill.", "Hydrochlorothiazide", "25 mg", "Essential hypertension", "I10"),
        "TR-M-HOPE": await chart("TR-M-HOPE", "Hope", "van Dyne", "1980-09-16", "Female", phar, "assessment", users["scott.lang@miners.utep.edu"], "Checked out", "Still tired in the afternoons. Takes her thyroid pill with coffee.", "Levothyroxine", "75 mcg", "Hypothyroidism", "E03.9", ("TSH", "6.2", "mIU/L", "0.4–4.0", "H")),
        "TR-X-SALAZAR": await chart("TR-X-SALAZAR", "Roberto", "Salazar", "1952-09-03", "Male", phar, "assessment", users["maria.gonzalez@miners.utep.edu"], "In progress", "Chest tightness when he walks to the store.", "Furosemide", "20 mg", "Chronic systolic heart failure", "I50.22", ("BNP", "640", "pg/mL", "<100", "H")),
        "TR-X-VEGA": await chart("TR-X-VEGA", "Leticia", "Vega", "1959-02-14", "Female", phar, "assessment", users["maria.gonzalez@miners.utep.edu"], "Checked out", "Swelling in both ankles since the calcium channel blocker.", "Amlodipine", "10 mg", "Essential hypertension", "I10"),
        "TR-X-CRUZ": await chart("TR-X-CRUZ", "Isabel", "Cruz", "1988-06-19", "Female", phar, "assessment", users["diego.ramirez@miners.utep.edu"], "Checked in", "Migraines most weeks. Uses the rescue medicine often.", "Sumatriptan", "50 mg", "Migraine, unspecified", "G43.909"),
        "TR-X-DELGADO": await chart("TR-X-DELGADO", "Fernando", "Delgado", "1970-11-07", "Male", phar, "assessment", users["diego.ramirez@miners.utep.edu"], "Checked out", "Muscle aches after the statin was increased.", "Atorvastatin", "40 mg", "Hyperlipidemia", "E78.5"),
        "TR-M-WILSON": await chart("TR-M-WILSON", "Sam", "Wilson", "1978-09-23", "Male", pt, "assessment", users["bucky.barnes@miners.utep.edu"], "Checked in", "Left shoulder pain after a weekend of painting.", "Ibuprofen", "400 mg", "Pain in left shoulder", "M25.512"),
        "TR-M-BISHOP": await chart("TR-M-BISHOP", "Kate", "Bishop", "1996-01-29", "Female", pt, "assessment", users["bucky.barnes@miners.utep.edu"], "In progress", "Right knee stiffness after ACL repair.", "Ibuprofen", "400 mg", "Status post right ACL reconstruction", "M23.91"),
        "TR-M-KNIGHT": await chart("TR-M-KNIGHT", "Misty", "Knight", "1982-06-06", "Female", pt, "assessment", users["jessica.jones@miners.utep.edu"], "In progress", "Right wrist stiffness after a fall.", "Acetaminophen", "500 mg", "Pain in right wrist", "M25.531"),
        "TR-M-WING": await chart("TR-M-WING", "Colleen", "Wing", "1986-01-15", "Female", pt, "assessment", users["jessica.jones@miners.utep.edu"], "Checked out", "Low back pain after a long drive.", "Naproxen", "220 mg", "Low back pain", "M54.50"),
        "TR-M-PAGE": await chart("TR-M-PAGE", "Karen", "Page", "1987-04-18", "Female", pt, "assessment", users["matt.murdock@miners.utep.edu"], "Checked in", "Neck pain that started at her desk.", "Ibuprofen", "400 mg", "Cervicalgia", "M54.2"),
        "TR-M-NELSON": await chart("TR-M-NELSON", "Foggy", "Nelson", "1986-10-03", "Male", pt, "assessment", users["matt.murdock@miners.utep.edu"], "Checked out", "Ankle still swollen two weeks after a sprain.", "Ibuprofen", "400 mg", "Sprain of right ankle", "S93.401A"),
        "TR-X-GALLEGOS": await chart("TR-X-GALLEGOS", "Hector", "Gallegos", "1983-04-02", "Male", pt, "assessment", users["andres.morales@miners.utep.edu"], "Checked in", "Low back pain after a warehouse shift.", "Naproxen", "220 mg", "Low back pain", "M54.50"),
        "TR-X-IBARRA": await chart("TR-X-IBARRA", "Yolanda", "Ibarra", "1961-01-28", "Female", pt, "assessment", users["andres.morales@miners.utep.edu"], "Checked out", "Shoulder stiffness. Hard to reach the top shelf.", "Ibuprofen", "400 mg", "Pain in right shoulder", "M25.511"),
        "TR-X-ORTIZ": await chart("TR-X-ORTIZ", "Camila", "Ortiz", "1995-07-11", "Female", pt, "assessment", users["valeria.castillo@miners.utep.edu"], "In progress", "Ankle sprain from a soccer game last week.", "Ibuprofen", "400 mg", "Sprain of right ankle", "S93.401A"),
        "TR-X-SOTO": await chart("TR-X-SOTO", "Rafael", "Soto", "1967-05-16", "Male", pt, "assessment", users["valeria.castillo@miners.utep.edu"], "Checked out", "Neck pain from driving a delivery route.", "Acetaminophen", "500 mg", "Cervicalgia", "M54.2"),
        "TR-M-CHAVEZ": await chart("TR-M-CHAVEZ", "America", "Chavez", "2001-06-01", "Female", pt, "assessment", luis, "Checked in", "Low back pain after a lifting shift.", "Naproxen", "220 mg", "Low back pain", "M54.50"),
    }

    pharm_pending = {"reason": "Follow-up from last week.", "recommendations": "Review the dose and what to watch for."}
    pharm_back = {"reason": "Student plan is too thin.", "recommendations": "Change the medicine."}
    pt_pending = {"subjective": "Pain with the activity that brought them in.", "measures": "Motion limited.", "plan": "Practice the movement. Recheck next visit."}
    pt_back = {"subjective": "Still limited.", "plan": "Keep going."}
    notes = [
        ("TR-M-FURY", "peter.parker@miners.utep.edu", "pending_review", gerardo, pharm_pending, None),
        ("TR-M-MAY", "peter.parker@miners.utep.edu", "returned", gerardo, pharm_back, "Name the dose you want her back on."),
        ("TR-M-PIETRO", "wanda.maximoff@miners.utep.edu", "pending_review", gerardo, pharm_pending, None),
        ("TR-M-VISION", "wanda.maximoff@miners.utep.edu", "returned", joe, pharm_back, "Offer the replacement medicine, not only a stop."),
        ("TR-M-WONG", "stephen.strange@miners.utep.edu", "pending_review", joe, pharm_pending, None),
        ("TR-M-PALMER", "stephen.strange@miners.utep.edu", "returned", gerardo, pharm_back, "Say what the next INR should be."),
        ("TR-M-LEWIS", "scott.lang@miners.utep.edu", "pending_review", gerardo, pharm_pending, None),
        ("TR-M-SELVIG", "scott.lang@miners.utep.edu", "returned", gerardo, pharm_back, "Check the potassium before you stop the water pill."),
        ("TR-M-HOPE", "scott.lang@miners.utep.edu", "cosigned", joe, pharm_pending, None),
        ("TR-X-SALAZAR", "maria.gonzalez@miners.utep.edu", "pending_review", gerardo, pharm_pending, None),
        ("TR-X-VEGA", "maria.gonzalez@miners.utep.edu", "returned", gerardo, pharm_back, "Name the medicine you would use instead."),
        ("TR-X-CRUZ", "diego.ramirez@miners.utep.edu", "pending_review", gerardo, pharm_pending, None),
        ("TR-X-DELGADO", "diego.ramirez@miners.utep.edu", "returned", gerardo, pharm_back, "Name a dose he could try before you stop the statin."),
        ("TR-M-WILSON", "bucky.barnes@miners.utep.edu", "pending_review", gerardo, pt_pending, None),
        ("TR-M-BISHOP", "bucky.barnes@miners.utep.edu", "returned", gerardo, pt_back, "Add the flexion you want by next week, and one exercise with sets and reps."),
        ("TR-M-KNIGHT", "jessica.jones@miners.utep.edu", "pending_review", gerardo, pt_pending, None),
        ("TR-M-WING", "jessica.jones@miners.utep.edu", "returned", gerardo, pt_back, "Add today's pain score and one exercise with sets and reps."),
        ("TR-M-PAGE", "matt.murdock@miners.utep.edu", "pending_review", gerardo, pt_pending, None),
        ("TR-M-NELSON", "matt.murdock@miners.utep.edu", "returned", gerardo, pt_back, "Add a swelling measure and the next visit goal."),
        ("TR-X-GALLEGOS", "andres.morales@miners.utep.edu", "pending_review", gerardo, pt_pending, None),
        ("TR-X-IBARRA", "andres.morales@miners.utep.edu", "returned", gerardo, pt_back, "Add the range you measured and one exercise with sets and reps."),
        ("TR-X-ORTIZ", "valeria.castillo@miners.utep.edu", "pending_review", gerardo, pt_pending, None),
        ("TR-X-SOTO", "valeria.castillo@miners.utep.edu", "returned", gerardo, pt_back, "Add today's rotation and a goal for the next visit."),
        ("TR-M-CHAVEZ", "luis", "pending_review", gerardo, pt_pending, None),
    ]
    for index, (mrn, author_key, status, reviewer, content, comment) in enumerate(notes):
        author = luis if author_key == "luis" else users[author_key]
        patient = charts[mrn]
        disc = pharmacy if patient.course_id == phar.id else therapy
        template = "pharmacy_mtm" if disc is pharmacy else "pt_daily_soap"
        signed = datetime(2026, 9, 11, 10 + (index % 6), tzinfo=timezone.utc)
        updated = datetime(2026, 9, 16, 9 + (index % 6), tzinfo=timezone.utc)
        note = await _ensure_note(
            db, patient, author, disc, reviewer if status != "draft" else None,
            status=status, template_id=template, content=content, diagnoses=[],
            created=signed, signed=None if status == "draft" else signed, updated=updated,
            cosigned=updated if status == "cosigned" else None,
            cosigned_by=reviewer if status == "cosigned" else None,
        )
        if comment:
            await _ensure_comment(db, note, reviewer, "returned", comment)

    await _ensure_appointment(db, charts["TR-M-STARK"].id, datetime(2026, 10, 9, 15, tzinfo=timezone.utc), "Heart failure check", "Pharmacy clinic")
    await _ensure_appointment(db, charts["TR-X-MORALES"].id, datetime(2026, 10, 12, 15, tzinfo=timezone.utc), "Blood pressure follow-up", "Pharmacy clinic")
    await _ensure_appointment(db, charts["TR-X-AGUILAR"].id, datetime(2026, 10, 15, 16, tzinfo=timezone.utc), "Knee evaluation", "Physical Therapy")
    await _ensure_audit(db, daniel.id, "chart.view", "patient", charts["TR-M-STARK"].id, phar.id, datetime(2026, 10, 5, 14, 10, tzinfo=timezone.utc))
    await _ensure_audit(db, users["maria.gonzalez@miners.utep.edu"].id, "note.sign_submit", "note", charts["TR-X-SALAZAR"].id, phar.id, datetime(2026, 10, 2, 15, 20, tzinfo=timezone.utc))
    await _ensure_audit(db, users["andres.morales@miners.utep.edu"].id, "chart.view", "patient", charts["TR-X-GALLEGOS"].id, pt.id, datetime(2026, 10, 4, 11, 5, tzinfo=timezone.utc))


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed EHR reference data")
    parser.add_argument("--admin-email", help="Create an extra admin account with this email")
    args = parser.parse_args()
    password = None
    if args.admin_email:
        password = getpass.getpass("Admin password (min 8 chars): ")
        if len(password) < 8:
            raise SystemExit("Password too short.")
        if password != getpass.getpass("Confirm password: "):
            raise SystemExit("Passwords don't match.")
    async def _run() -> None:
        await seed(args.admin_email, password)
        await engine.dispose()

    asyncio.run(_run())


if __name__ == "__main__":
    main()
